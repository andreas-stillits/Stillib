from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TypeVar

from .core import RNGStream
from .provenance import RNGManifest

TaskType = TypeVar("TaskType")


@dataclass(frozen=True, slots=True)
class TaskStream[TaskType]:
    task: TaskType
    manifest: RNGManifest


def assign_streams(
    tasks: Iterable[TaskType],
    root_stream: RNGStream,
    *,
    task_namer: Callable[[TaskType], str] | None = None,
) -> list[TaskStream[TaskType]]:
    assigned: list[TaskStream[TaskType]] = []

    for index, task in enumerate(tasks):
        label = task_namer(task) if task_namer is not None else f"task-{index}"
        child = root_stream.spawn(label)
        assigned.append(TaskStream(task, child.manifest()))

    return assigned


def stream_for_task(
    root_stream: RNGStream,
    label: str,
) -> RNGManifest:
    return root_stream.spawn(label).manifest()
