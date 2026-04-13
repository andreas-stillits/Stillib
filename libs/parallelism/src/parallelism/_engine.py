from __future__ import annotations

import os
import time
import traceback as tb
from collections.abc import Callable, Iterable, Iterator, Sized
from concurrent.futures import (
    FIRST_COMPLETED,
    Future,
    ProcessPoolExecutor,
    wait,
)
from typing import Any

from .models import (
    CompletedTask,
    FailedTask,
    InputType,
    OutputType,
    ProgressUpdate,
    TaskOutcome,
)


# helper to attempt a count of total tasks, returns None if not possible (e.g. if tasks is a generator)
def _attempt_len(tasks: Iterable[InputType]) -> int | None:
    # if __len__ is implemented, return it, else return None
    if isinstance(tasks, Sized):
        return len(tasks)
    return None


# helper to assign a task name
def _task_name(
    index: int,
    task: InputType,
    task_namer: Callable[[InputType], str] | None = None,
) -> str:
    # if task_namer is provided, use it to get the task name, else default to "task-{index}"
    if task_namer is not None:
        return task_namer(task)
    return f"task-{index}"


# helper to execute a single task and catch exceptions associated with worker_function execution
def _run_task(
    task: Any, worker_function: Callable[[Any], Any]
) -> tuple[bool, Any, float]:
    """
    Run a single task and catch exceptions gracefully
    Args:
        task: The task to run
        worker_function: The function to run the task with
    Returns:
        A tuple of (success, result / failure_info, elapsed_time)
    """
    started = time.perf_counter()
    try:
        result = worker_function(task)
    except Exception as exc:
        failure = {
            "exc_type": type(exc).__name__,
            "exc_message": str(exc),
            "traceback": tb.format_exc(),
        }
        return False, failure, time.perf_counter() - started
    else:
        return True, result, time.perf_counter() - started


# the main engine function, which lazily submits tasks to the executor, keeps a bounded number of tasks inflight,
# and yields TaskOutcomes as they complete, regardless of submission order.
def _iter_outcomes_as_completed(
    tasks: Iterable[InputType],
    worker_function: Callable[[InputType], OutputType],
    *,
    max_workers: int | None = None,
    buffersize: int | None = None,
    initializer: Callable[..., Any] | None = None,
    initargs: tuple[Any, ...] = (),
    progress_callback: Callable[[ProgressUpdate], None] | None = None,
    task_namer: Callable[[InputType], str] | None = None,
) -> Iterator[TaskOutcome[InputType, OutputType]]:
    """
    Internal engine. Submits tasks lazily, keeps a bounded number of futures in flight,
    and yields TaskOutcomes in completion order.
    Args:
        tasks (Iterable): An iterable of tasks to run. Can be a generator or a list
        worker_function (Callable): A function that takes a single task and returns a result.
        max_workers (int, optional): The maximum number of worker processes to use. Defaults to CPU core count.
        buffersize (int, optional): The maximum number of tasks to have inflight at once. Defaults to 2 * resolved number of workers.
        initializer (Callable, optional): A function to initialize each worker process. Defaults to None.
        initargs (tuple, optional): Arguments to pass to the initializer. Defaults to ().
        progress_callback (Callable, optional): A function that takes a ProgressUpdate and is called after each task completion. Defaults to None.
        task_namer (Callable, optional): A function that takes a task and returns a string name for it. Defaults to None, which will use "task-{index}".
    Returns:
        An iterator of TaskOutcomes as returned by the worker function, in completion order.
    Raises:
        KeyboardInterrupt: If the run is interrupted by a KeyboardInterrupt.
    """

    # resolve optionals
    resolved_workers = max_workers or (os.cpu_count() or 1)
    resolved_buffersize = buffersize or (2 * resolved_workers)

    # validate optionals
    if resolved_workers < 1:
        raise ValueError("max_workers must be >= 1")
    if resolved_buffersize < 1:
        raise ValueError("buffersize must be >= 1")

    # book keeping for task submission and progress tracking
    task_iterator = enumerate(tasks)
    total: int | None = _attempt_len(tasks)
    submitted: int = 0
    completed: int = 0
    failures: int = 0
    started: float = time.perf_counter()

    # dictionary mapping futures to their corresponding task index and input
    inflight: dict[Future[tuple[bool, Any, float]], tuple[int, InputType]] = {}

    # helper to emit progress updates after each task completion, if progress_callback is provided
    def _emit_progress() -> None:
        if progress_callback is None:
            return
        progress_callback(
            ProgressUpdate(
                submitted=submitted,
                completed=completed,
                failures=failures,
                running=submitted - completed - failures,
                total=total,
                elapsed_time=time.perf_counter() - started,
            )
        )

    # helper to classify a completed future as a CompletedTask or FailedTask and return the appropriate TaskOutcome
    def _retrieve_outcome(
        index: int, task: InputType, future: Future[tuple[bool, Any, float]]
    ) -> TaskOutcome[InputType, OutputType]:
        # declare nonlocal to update progress counts within this helper
        nonlocal completed, failures

        # catch exceptions that originate from the ProcessPool infrastructure itself, rather than from worker_function
        try:
            success, payload, elapsed_time = future.result()
        except Exception as exc:
            # this should only happen if something went wrong with the execution environment itself
            # rather than the worker function, since _run_task should catch exceptions from the worker function
            failures += 1
            return FailedTask(
                index=index,
                task=task,
                task_name=_task_name(index, task, task_namer),
                exc_type=type(exc).__name__,
                exc_message=str(exc),
                traceback=tb.format_exc(),
                infrastructure_error=True,  # mark as true for debugging
                elapsed_time=time.perf_counter() - started,
            )

        # if the future completed successfully, we yield a CompletedTask
        if success:
            completed += 1
            return CompletedTask(
                index=index,
                task=task,
                task_name=_task_name(index, task, task_namer),
                result=payload,
                elapsed_time=elapsed_time,
            )
        # if the future raised an exception, we yield a FailedTask and info
        else:
            failures += 1
            return FailedTask(
                index=index,
                task=task,
                task_name=_task_name(index, task, task_namer),
                exc_type=payload["exc_type"],
                exc_message=payload["exc_message"],
                traceback=payload["traceback"],
                infrastructure_error=False,
                elapsed_time=elapsed_time,
            )

    # initialze the executor
    executor = ProcessPoolExecutor(
        max_workers=resolved_workers,
        initializer=initializer,
        initargs=initargs,
    )

    # boolean flag to indicate if we are done with all tasks
    exhausted = False
    # flag to track if we've called shutdown on the executor, to avoid calling it multiple times in case of KeyboardInterrupt
    shutdown_called = False

    # inflight tracks pending futures < resolved_buffersize, exhausted tracks if we've submitted all tasks
    # and we loop until both conditions are met

    # wrap for executor shutdown logic
    try:
        # wrap for KeyboardInterrupt on Ctrl+C to allow graceful shutdown
        try:
            # while pending tasks or tasks waiting to be submitted
            while inflight or not exhausted:
                # while the buffer is not full and further tasks can be submitted
                while not exhausted and len(inflight) < resolved_buffersize:

                    # get next task, if any
                    try:
                        index, task = next(task_iterator)

                    # break out to wait for inflight tasks to complete and yield results,
                    # if no more tasks to submit
                    except StopIteration:
                        exhausted = True
                        break

                    # submit the next task and track its future
                    future = executor.submit(_run_task, task, worker_function)
                    # map this future to its task index and input for later retrieval
                    inflight[future] = (index, task)
                    submitted += 1
                    _emit_progress()
                # At this point we've submitted buffersize tasks to be inflight

                # if no tasks are inflight, we are done
                if not inflight:
                    break  # breaks out of both while loops

                # wait until at least one of the inflight futures completes
                done, _ = wait(tuple(inflight), return_when=FIRST_COMPLETED)

                # when the first future has completed,
                # we yield its result and remove it from the inflight dict
                for future in done:
                    # remove from inflight an retrieve index, task input
                    index, task = inflight.pop(future)
                    # return status, payload and elapsed time of the completed future
                    yield _retrieve_outcome(index, task, future)
                    _emit_progress()

        # If the user interrupts the run with Ctrl+C, shut down the executor gracefully
        except KeyboardInterrupt:
            # what futures are finished?
            done_now = [
                (future, origin) for future, origin in inflight.items() if future.done()
            ]

            # cancel those pending that are not finished
            for future in inflight:
                if not future.done():
                    future.cancel()

            # yield results that are already done, and emit progress updates for them
            for future, (index, task) in done_now:
                yield _retrieve_outcome(index, task, future)
                _emit_progress()

            # shut down the executor immediately, canceling any pending tasks that haven't started yet
            executor.shutdown(wait=False, cancel_futures=True)
            shutdown_called = True  # flag that the executor has been shut down to avoid trying to shut it down again in the finally block
            raise  # re-raise the error to be caught in the caller

    # regardless of any exceptions, ensure we shut down the executor to free resources, unless we've already done so in the KeyboardInterrupt except block
    finally:
        if not shutdown_called:
            executor.shutdown(
                wait=True, cancel_futures=False
            )  # wait for running tasks to complete, but don't cancel any pending tasks


# helper to reorder outcomes from completion order to submission order, if the user requested input order
def _iter_outcomes_as_submitted(
    outcomes: Iterator[TaskOutcome[InputType, OutputType]],
) -> Iterator[TaskOutcome[InputType, OutputType]]:
    """
    Yields task outcomes in input order (by index)
    OBS: this keeps outcomes in memory until the earliest pending task completes.
         Can thus be as memory intensive as a collect call
    """
    pending: dict[int, TaskOutcome[InputType, OutputType]] = {}
    next_expected = 0

    for outcome in outcomes:
        pending[outcome.index] = outcome

        while next_expected in pending:
            yield pending.pop(next_expected)
            next_expected += 1
