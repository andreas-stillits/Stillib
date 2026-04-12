from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Iterator
from typing import Any

from ._engine import _iter_outcomes
from .models import (
    CompletedTask,
    ErrorPolicy,
    FailedTask,
    InputType,
    InterruptPolicy,
    OutputType,
    ParallelRunInterrupted,
    ProgressUpdate,
    RunReport,
    TaskExecutionError,
    TaskOutcome,
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
    interrupt_policy: InterruptPolicy = "cancel",
) -> Iterator[TaskOutcome[InputType, OutputType] | OutputType]:
    """
    Run tasks in parallel and yield results as they come in.

    Fail-fast and streaming
    Raises TaskExecutionError on the first failed task.
    Raises KeyboardInterrupt on Ctrl+C, with behavior depending on interrupt_policy.
    """

    for outcome in _iter_outcomes(
        tasks,
        worker_function,
        max_workers=max_workers,
        buffersize=buffersize,
        initializer=initializer,
        initargs=initargs,
        progress_callback=progress_callback,
        task_namer=task_namer,
        interrupt_policy=interrupt_policy,
    ):
        if isinstance(outcome, FailedTask):
            raise TaskExecutionError(outcome)
        yield outcome.result if isinstance(outcome, CompletedTask) else outcome


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
    interrupt_policy: InterruptPolicy = "cancel",
    error_policy: ErrorPolicy = "raise",
) -> RunReport[InputType, OutputType]:
    """
    Collection API.
    """

    if error_policy not in {"raise", "collect"}:
        raise ValueError(
            f"Invalid error_policy: {error_policy}. Must be 'raise' or 'collect'."
        )

    time_start = time.perf_counter()
    completed: list[CompletedTask[InputType, OutputType]] = []
    failures: list[FailedTask[InputType]] = []

    try:

        for outcome in _iter_outcomes(
            tasks,
            worker_function,
            max_workers=max_workers,
            buffersize=buffersize,
            initializer=initializer,
            initargs=initargs,
            progress_callback=progress_callback,
            task_namer=task_namer,
            interrupt_policy=interrupt_policy,
        ):
            if isinstance(outcome, FailedTask):
                if error_policy == "raise":
                    raise TaskExecutionError(outcome)
                failures.append(outcome)
            else:
                completed.append(outcome)

    except KeyboardInterrupt as exc:
        report = RunReport(
            completed=completed,
            failed=failures,
            interrupted=True,
            elapsed_time=time.perf_counter() - time_start,
        )
        if error_policy == "collect":
            return report
        raise ParallelRunInterrupted(report) from exc

    return RunReport(
        completed=completed,
        failed=failures,
        interrupted=False,
        elapsed_time=time.perf_counter() - time_start,
    )
