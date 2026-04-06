from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Iterator
from typing import Any

from ._engine import _iter_outcomes
from .models import (
    ErrorPolicy,
    InputType,
    InterruptPolicy,
    Ordering,
    OutputType,
    ParallelRunInterrupted,
    ProgressUpdate,
    RunReport,
    TaskExecutionError,
    TaskFailure,
    TaskOutcome,
    TaskSuccess,
)


def stream_parallel(
    tasks: Iterable[InputType],
    worker_function: Callable[[InputType], OutputType],
    *,  # enforce keyword only for better readability
    max_workers: int | None = None,
    ordering: Ordering = "completion",
    batch_size: int = 1,
    buffersize: int | None = None,
    initializer: Callable[..., Any] | None = None,
    init_args: tuple[Any, ...] = (),
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
        ordering=ordering,
        batch_size=batch_size,
        buffersize=buffersize,
        initializer=initializer,
        init_args=init_args,
        progress_callback=progress_callback,
        task_namer=task_namer,
        interrupt_policy=interrupt_policy,
    ):
        if isinstance(outcome, TaskFailure):
            raise TaskExecutionError(outcome)
        yield outcome.result if isinstance(outcome, TaskSuccess) else outcome


def collect_parallel(
    tasks: Iterable[InputType],
    worker_function: Callable[[InputType], OutputType],
    *,  # enforce keyword only for better readability
    max_workers: int | None = None,
    ordering: Ordering = "completion",
    batch_size: int = 1,
    buffersize: int | None = None,
    initializer: Callable[..., Any] | None = None,
    init_args: tuple[Any, ...] = (),
    error_policy: ErrorPolicy = "raise",
    progress_callback: Callable[[ProgressUpdate], None] | None = None,
    task_namer: Callable[[InputType], str] | None = None,
    interrupt_policy: InterruptPolicy = "cancel",
) -> RunReport[InputType, OutputType] | list[OutputType]:
    """
    Collection API.

    error_policy: "raise"
        returns list[OutputType], fail-fast on first failure

    error_policy: "collect"
        returns RunReport[InputType, OutputType], aggregating successes/failures
        and returning a partial report if interrupted
    """
    if error_policy not in ("raise", "collect"):
        raise ValueError("error_policy must be either 'raise' or 'collect'")

    time_start = time.perf_counter()
    successes: list[TaskSuccess[InputType, OutputType]] = []
    failures: list[TaskFailure[InputType]] = []

    try:
        for outcome in _iter_outcomes(
            tasks,
            worker_function,
            max_workers=max_workers,
            ordering=ordering,
            batch_size=batch_size,
            buffersize=buffersize,
            initializer=initializer,
            init_args=init_args,
            progress_callback=progress_callback,
            task_namer=task_namer,
            interrupt_policy=interrupt_policy,
        ):
            if isinstance(outcome, TaskFailure):
                if error_policy == "raise":
                    report = RunReport(
                        successes=successes.copy(),
                        failures=[*failures, outcome],
                        interrupted=False,
                        duration=time.perf_counter() - time_start,
                    )
                    raise TaskExecutionError(outcome, partial_report=report)
                failures.append(outcome)
            else:
                successes.append(outcome)

    except KeyboardInterrupt as exc:
        report = RunReport(
            successes=successes,
            failures=failures,
            interrupted=True,
            duration=time.perf_counter() - time_start,
        )
        if error_policy == "collect":
            return report
        raise ParallelRunInterrupted(report) from exc

    if error_policy == "collect":
        return RunReport(
            successes=successes,
            failures=failures,
            interrupted=False,
            duration=time.perf_counter() - time_start,
        )

    return [item.result for item in successes]
