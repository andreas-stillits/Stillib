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

from .batching import default_buffersize
from .models import (
    InputType,
    InterruptPolicy,
    Ordering,
    OutputType,
    ProgressUpdate,
    TaskFailure,
    TaskOutcome,
    TaskSuccess,
    _BatchItem,
    _BatchItemFailure,
    _BatchItemSuccess,
    _BatchSubmission,
)


def _iter_outcomes(
    tasks: Iterable[InputType],
    worker_function: Callable[[InputType], OutputType],
    *,
    max_workers: int | None,
    ordering: Ordering,
    batch_size: int,
    buffersize: int | None,
    initializer: Callable[..., Any] | None,
    init_args: tuple[Any, ...],
    progress_callback: Callable[[ProgressUpdate], None] | None,
    task_namer: Callable[[InputType], str] | None,
    interrupt_policy: InterruptPolicy,
) -> Iterator[TaskOutcome[InputType, OutputType]]:
    """
    Core engine for stream_parallel, yielding TaskOutcome objects as they come in.
    See stream_parallel in for user-facing docstring and parameter validation.
    """
    if ordering not in ("completion", "input"):
        raise ValueError("ordering must be 'completion' or 'input'")
    if interrupt_policy not in ("cancel", "drain"):
        raise ValueError("interrupt_policy must be 'cancel' or 'drain'")
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    resolved_workers = max_workers or (os.cpu_count() or 1)
    resolved_buffersize = buffersize or default_buffersize(resolved_workers)
    if resolved_buffersize < 1:
        raise ValueError("buffersize must be >= 1")

    total = _maybe_len(tasks)
    time_start = time.perf_counter()
    submitted = 0
    completed = 0
    failed = 0

    def emit_progress() -> None:
        if progress_callback is None:
            return
        progress_callback(
            ProgressUpdate(
                submitted,
                completed,
                failed,
                running=submitted - completed - failed,
                total=total,
                duration=time.perf_counter() - time_start,
            )
        )

    indexed_batches = _indexed_batches(tasks, batch_size)
    inflight: dict[
        Future[list[_BatchItem[OutputType]]], _BatchSubmission[InputType]
    ] = {}
    pending_by_index: dict[int, TaskOutcome[InputType, OutputType]] = {}
    next_expected_index = 0

    executor = ProcessPoolExecutor(
        max_workers=resolved_workers,
        initializer=initializer,
        initargs=init_args,
    )
    shutdown_called = False

    def submit_until_full(stop_submitting: bool = False) -> bool:
        nonlocal submitted

        if stop_submitting:
            return False

        exhausted = False

        while len(inflight) < resolved_buffersize:
            try:
                batch = next(indexed_batches)
            except StopIteration:
                exhausted = True
                break

            future = executor.submit(_run_batch, batch.tasks, worker_function)
            inflight[future] = batch
            submitted += len(batch.tasks)
            emit_progress()

        return exhausted

    def outcomes_from_done(
        done_futures: set[Future[list[_BatchItem[OutputType]]]],
        *,
        force_flush_all_input_ready: bool = False,
    ) -> list[TaskOutcome[InputType, OutputType]]:
        nonlocal completed, failed, next_expected_index

        ready: list[TaskOutcome[InputType, OutputType]] = []

        for future in done_futures:
            batch = inflight.pop(future, None)
            if batch is None:
                continue

            if future.cancelled():
                continue

            try:
                batch_items = future.result()
            except Exception as exc:  # pool-level failure, not worker_function failure
                batch_start = batch.indexes[0] if batch.indexes else -1
                raise RuntimeError(
                    f"Process pool failed while executing batch "
                    f"starting at input index {batch_start}"
                ) from exc

            for item in batch_items:
                index = batch.indexes[item.position]
                task = batch.tasks[item.position]
                task_name = _task_name(index, task, task_namer)

                if isinstance(item, _BatchItemSuccess):
                    outcome: TaskOutcome[InputType, OutputType] = TaskSuccess(
                        index,
                        task,
                        task_name,
                        item.result,
                        item.duration,
                    )
                    completed += 1
                else:
                    outcome = TaskFailure(
                        index,
                        task,
                        task_name,
                        item.exc_type,
                        item.exc_message,
                        item.traceback,
                        item.duration,
                    )
                    failed += 1

                if ordering == "completion":
                    ready.append(outcome)
                else:
                    pending_by_index[index] = outcome

        if ordering == "input":
            if force_flush_all_input_ready:
                for index in sorted(pending_by_index):
                    ready.append(pending_by_index[index])
                pending_by_index.clear()
            else:
                while next_expected_index in pending_by_index:
                    ready.append(pending_by_index.pop(next_expected_index))
                    next_expected_index += 1

        emit_progress()
        return ready

    try:
        source_exhausted = submit_until_full(stop_submitting=False)

        while inflight or not source_exhausted:
            if not inflight:
                source_exhausted = submit_until_full(stop_submitting=False)
                if not inflight and source_exhausted:
                    break

            done, _ = wait(
                tuple(inflight),
                timeout=0.1,
                return_when=FIRST_COMPLETED,
            )

            if done:
                for outcome in outcomes_from_done(done):
                    yield outcome

            source_exhausted = submit_until_full(stop_submitting=False)

    except KeyboardInterrupt:
        if interrupt_policy == "drain":
            # Stop submitting new work, but let everything already submitted finish.
            while inflight:
                done, _ = wait(tuple(inflight), return_when=FIRST_COMPLETED)
                for outcome in outcomes_from_done(done):
                    yield outcome

            executor.shutdown(wait=True, cancel_futures=False)
            shutdown_called = True
            raise

        # interrupt_policy == "cancel"
        # Cancel pending futures if possible, rescue only futures already done.
        done_now = {future for future in inflight if future.done()}
        for future in list(inflight):
            if future not in done_now:
                future.cancel()

        for outcome in outcomes_from_done(
            done_now,
            force_flush_all_input_ready=(ordering == "input"),
        ):
            yield outcome

        executor.shutdown(wait=False, cancel_futures=True)
        shutdown_called = True
        raise

    finally:
        if not shutdown_called:
            executor.shutdown(wait=True, cancel_futures=False)


def _indexed_batches(
    tasks: Iterable[InputType], batch_size: int
) -> Iterator[_BatchSubmission[InputType]]:
    batch_indexes: list[int] = []
    batch_tasks: list[InputType] = []

    for index, task in enumerate(tasks):
        batch_indexes.append(index)
        batch_tasks.append(task)

        if len(batch_tasks) >= batch_size:
            yield _BatchSubmission(indexes=batch_indexes, tasks=batch_tasks)
            batch_indexes = []
            batch_tasks = []

    if batch_tasks:
        yield _BatchSubmission(indexes=batch_indexes, tasks=batch_tasks)


def _maybe_len(tasks: Iterable[Any]) -> int | None:
    return len(tasks) if isinstance(tasks, Sized) else None


def _task_name(
    index: int,
    task: InputType,
    task_namer: Callable[[InputType], str] | None,
) -> str:
    if task_namer is not None:
        return task_namer(task)
    return f"task-{index}"


def _run_batch(
    batch_tasks: list[Any],
    worker_function: Callable[[Any], Any],
) -> list[_BatchItem[Any]]:
    outcomes: list[_BatchItem[Any]] = []

    for position, task in enumerate(batch_tasks):
        started = time.perf_counter()
        try:
            result = worker_function(task)
        except Exception as exc:
            outcomes.append(
                _BatchItemFailure(
                    position,
                    type(exc).__name__,
                    str(exc),
                    traceback.format_exc(),
                    duration=time.perf_counter() - started,
                )
            )
        else:
            outcomes.append(
                _BatchItemSuccess(
                    position,
                    result,
                    duration=time.perf_counter() - started,
                )
            )

    return outcomes
