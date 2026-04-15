from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TypeVar

from .core import RNGStream
from .manifest import RNGManifest


@dataclass(frozen=True, slots=True)
class TaskStream[TaskType]:
    task: TaskType
    manifest: RNGManifest


def assign_streams[Task](
    tasks: Iterable[Task],
    root_stream: RNGStream,
    *,
    task_namer: Callable[[Task], str] | None = None,
) -> list[TaskStream[Task]]:
    assigned: list[TaskStream[Task]] = []

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
