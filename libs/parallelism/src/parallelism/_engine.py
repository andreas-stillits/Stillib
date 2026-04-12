from __future__ import annotations

import os
import time
import traceback
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
    InterruptPolicy,
    OutputType,
    ProgressUpdate,
    TaskOutcome,
)


def _attempt_len(tasks: Iterable[InputType]) -> int | None:
    if isinstance(tasks, Sized):
        return len(tasks)
    return None


def _task_name(
    index: int,
    task: InputType,
    task_namer: Callable[[InputType], str] | None = None,
) -> str:
    if task_namer is not None:
        return task_namer(task)
    return f"Task-{index}"


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
            "traceback": traceback.format_exc(),
        }
        return False, failure, time.perf_counter() - started
    else:
        return True, result, time.perf_counter() - started


def _iter_outcomes(
    tasks: Iterable[InputType],
    worker_function: Callable[[InputType], OutputType],
    *,
    max_workers: int | None = None,
    buffersize: int | None = None,
    initializer: Callable[..., Any] | None = None,
    initargs: tuple[Any, ...] = (),
    progress_callback: Callable[[ProgressUpdate], None] | None = None,
    task_namer: Callable[[InputType], str] | None = None,
    interrupt_policy: InterruptPolicy = "cancel",
) -> Iterator[TaskOutcome[InputType, OutputType]]:
    """
    Internal engine.

    Submits tasks lazily, keeps a bounded number of futures in flight,
    and yields TaskOutcomes in completion order.
    """
    resolved_workers = max_workers or (os.cpu_count() or 1)
    resolved_buffersize = buffersize or (2 * resolved_workers)

    if resolved_workers < 1:
        raise ValueError("max_workers must be >= 1")
    if resolved_buffersize < 1:
        raise ValueError("buffersize must be >= 1")

    task_iterator = enumerate(tasks)
    total: int | None = _attempt_len(tasks)
    submitted: int = 0
    completed: int = 0
    failed: int = 0
    started: float = time.perf_counter()

    # dictionary mapping futures to their corresponding task index and input
    inflight: dict[Future[tuple[bool, Any, float]], tuple[int, InputType]] = {}

    with ProcessPoolExecutor(
        max_workers=resolved_workers,
        initializer=initializer,
        initargs=initargs,
    ) as executor:
        # Submit batch of tasks

        # boolean flag to indicate if the buffer is empty
        exhausted = False

        # inflight tracks pending futures, exhausted tracks if we've submitted all tasks
        # and we loop until both conditions are met
        while inflight or not exhausted:
            # within a single buffersize batch
            while not exhausted and len(inflight) < resolved_buffersize:

                # get next task, if any, else break to start new submission
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
            # At this point we've submitted as many as buffersize tasks to be inflight

            # if no tasks are inflight, we are done
            if not inflight:
                break  # breaks out of both while loops

            # wait until the first of the inflight futures
            done, _ = wait(tuple(inflight), return_when=FIRST_COMPLETED)

            # when the first future has completed,
            # we yield its result and remove it from the inflight dict
            for future in done:
                # remove from inflight an retrieve index, task input
                index, task = inflight.pop(future)
                # return status, payload and elapsed time of the completed future
                success, payload, elapsed_time = future.result()

                # if the future completed successfully, we yield a CompletedTask
                if success:
                    yield CompletedTask(
                        index=index,
                        task=task,
                        task_name=_task_name(index, task, task_namer),
                        result=payload,
                        elapsed_time=elapsed_time,
                    )
                    completed += 1
                # if the future raised an exception, we yield a FailedTask and info
                else:
                    yield FailedTask(
                        index=index,
                        task=task,
                        task_name=_task_name(index, task, task_namer),
                        exc_type=payload["exc_type"],
                        exc_message=payload["exc_message"],
                        traceback=payload["traceback"],
                        elapsed_time=elapsed_time,
                    )
                    failed += 1

                # if we have a progress callback, we call it with the current progress
                if progress_callback is None:
                    continue
                progress_callback(
                    ProgressUpdate(
                        submitted=submitted,
                        completed=completed,
                        failed=failed,
                        running=submitted - completed - failed,
                        total=total,
                        elapsed_time=time.perf_counter() - started,
                    )
                )
