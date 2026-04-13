from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Iterator
from typing import Any

from ._engine import _iter_outcomes_as_completed, _iter_outcomes_as_submitted
from .models import (
    CompletedTask,
    ErrorPolicy,
    FailedTask,
    InputType,
    Ordering,
    OutputType,
    ParallelRunInterrupted,
    ProgressUpdate,
    RunReport,
    TaskExecutionError,
)


def stream(
    tasks: Iterable[InputType],
    worker_function: Callable[[InputType], OutputType],
    *,  # enforce keyword only for better readability
    max_workers: int | None = None,
    buffersize: int | None = None,
    initializer: Callable[..., Any] | None = None,
    initargs: tuple[Any, ...] = (),
    progress_callback: Callable[[ProgressUpdate], None] | None = None,
    task_namer: Callable[[InputType], str] | None = None,
    ordering: Ordering = "completion",
) -> Iterator[OutputType]:
    """
    Streaming API to run tasks in parallel and yield results as they come in, with fail-fast behavior on errors.
    Args:
        tasks (Iterable): An iterable of tasks to run. Can be a generator or a list.
        worker_function (Callable): A function that takes a single task and returns a result.
        max_workers (int, optional): The maximum number of worker processes to use. Defaults to CPU core count.
        buffersize (int, optional): The maximum number of tasks to have inflight at once. Defaults to 2 * resolved number of workers.
        initializer (Callable, optional): A function to initialize each worker process. Defaults to None.
        initargs (tuple, optional): Arguments to pass to the initializer. Defaults to ().
        progress_callback (Callable, optional): A function that takes a ProgressUpdate and is called after each task completion. Defaults to None.
        task_namer (Callable, optional): A function that takes a task and returns a string name for it. Defaults to None, which will use "task-{index}".
        ordering (str, optional): The order to yield results in. "completion" or "input". Defaults to "completion".
    Returns:
        An iterator of task outcomes as returned by the worker function.
    Raises:
        TaskExecutionError: If the error_policy is "raise" and any task fails.
        KeyboardInterrupt: If the run is interrupted by a KeyboardInterrupt.

    """

    # validate ordering argument
    if ordering not in {"completion", "input"}:
        raise ValueError(
            f"Invalid ordering: {ordering}. Must be 'completion' or 'input'."
        )

    # iterator over task outcomes in completion order
    outcomes = _iter_outcomes_as_completed(
        tasks,
        worker_function,
        max_workers=max_workers,
        buffersize=buffersize,
        initializer=initializer,
        initargs=initargs,
        progress_callback=progress_callback,
        task_namer=task_namer,
    )

    # if input order requested, reorder using a simple wrapper
    # OBS: This will buffer all outcomes in memory until the earliest task completes
    if ordering == "input":
        outcomes = _iter_outcomes_as_submitted(outcomes)

    # yield results or raise on failures as they come in
    for outcome in outcomes:
        if isinstance(outcome, FailedTask):
            raise TaskExecutionError(outcome)
        yield outcome.result


def collect(
    tasks: Iterable[InputType],
    worker_function: Callable[[InputType], OutputType],
    *,  # enforce keyword only for better readability
    max_workers: int | None = None,
    buffersize: int | None = None,
    initializer: Callable[..., Any] | None = None,
    initargs: tuple[Any, ...] = (),
    progress_callback: Callable[[ProgressUpdate], None] | None = None,
    task_namer: Callable[[InputType], str] | None = None,
    ordering: Ordering = "input",
    error_policy: ErrorPolicy = "raise",
) -> RunReport[InputType, OutputType]:
    """
    Collection API to run tasks in parallel and collect results and failures in a report.
    Args:
        tasks (Iterable): An iterable of tasks to run. Can be a generator or a list
        worker_function (Callable): A function that takes a single task and returns a result.
        max_workers (int, optional): The maximum number of worker processes to use. Defaults to CPU core count.
        buffersize (int, optional): The maximum number of tasks to have inflight at once. Defaults to 2 * resolved number of workers.
        initializer (Callable, optional): A function to initialize each worker process. Defaults to None.
        initargs (tuple, optional): Arguments to pass to the initializer. Defaults to ().
        progress_callback (Callable, optional): A function that takes a ProgressUpdate and is called after each task completion. Defaults to None.
        task_namer (Callable, optional): A function that takes a task and returns a string name for it. Defaults to use "task-{index}".
        ordering (str, optional): The order to process results in. "completion" or "input". Defaults to "input".
        error_policy (str, optional): The policy for handling task errors. "raise" to raise immediately, "collect" to collect in the report. Defaults to "raise".
    Returns:
        RunReport: A report containing lists of completed tasks and failed tasks, as well as overall metadata
    Raises:
        TaskExecutionError: If error_policy is "raise" and any task fails.
        ParallelRunInterrupted: If the run is interrupted by a KeyboardInterrupt.
    """

    # validate error policy and ordering argument
    if error_policy not in {"raise", "collect"}:
        raise ValueError(
            f"Invalid error_policy: {error_policy}. Must be 'raise' or 'collect'."
        )
    if ordering not in {"completion", "input"}:
        raise ValueError(
            f"Invalid ordering: {ordering}. Must be 'completion' or 'input'."
        )

    # track time and results
    time_start = time.perf_counter()
    completed: list[CompletedTask[InputType, OutputType]] = []
    failures: list[FailedTask[InputType]] = []

    # catch user KeyboardInterrupt on Ctrl+C and wrap in ParallelRunInterrupted with a partial report for debugging
    try:
        # iterate over outcomes in completion order
        for outcome in _iter_outcomes_as_completed(
            tasks,
            worker_function,
            max_workers=max_workers,
            buffersize=buffersize,
            initializer=initializer,
            initargs=initargs,
            progress_callback=progress_callback,
            task_namer=task_namer,
        ):
            # if a task failed
            if isinstance(outcome, FailedTask):
                # if fail-fast, raise immediately with the failure and a partial report
                if error_policy == "raise":
                    report = RunReport(
                        completed=completed,
                        failures=[*failures, outcome],
                        interrupted=False,
                        elapsed_time=time.perf_counter() - time_start,
                    )
                    raise TaskExecutionError(outcome, partial_report=report)
                # if collecting errors, append to failures and continue
                failures.append(outcome)
            # if the task succeeded, append to completed
            else:
                completed.append(outcome)

    # catch and wrap KeyboardInterrupt
    except KeyboardInterrupt as exc:
        # construct partial report
        report = RunReport(
            completed=completed,
            failures=failures,
            interrupted=True,
            elapsed_time=time.perf_counter() - time_start,
        )
        # return report if collecting errors, otherwise raise ParallelRunInterrupted with the report attached for debugging
        if error_policy == "collect":
            return report
        raise ParallelRunInterrupted(report) from exc

    # if all outcomes received without interruption
    # sort by input order if requested
    if ordering == "input":
        # sort completed and failed by their original input order
        completed.sort(key=lambda item: item.index)
        failures.sort(key=lambda item: item.index)

    # return final report with all completed and failed tasks
    return RunReport(
        completed=completed,
        failures=failures,
        interrupted=False,
        elapsed_time=time.perf_counter() - time_start,
    )
