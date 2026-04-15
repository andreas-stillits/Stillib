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
    prefix: str = "task",
) -> list[TaskStream[Task]]:
    """
    Assign a unique RNGStream to each task, derived from a root stream, and return a list of TaskStream objects containing the task and its RNG manifest.
    Args:
        tasks: An iterable of tasks to assign RNG streams to.
        root_stream: The root RNGStream from which all task streams will be derived.
        prefix: An optional prefix for the labels of the assigned streams. If not provided, labels will be generated as "task-0", "task-1", etc.

    """
    num_tasks = len(list(tasks))
    streams: list[RNGStream] = root_stream.spawn_many(
        num_tasks,
        prefix=prefix,
    )

    return [
        TaskStream(
            task,
            stream.manifest(),
        )
        for task, stream in zip(tasks, streams, strict=True)
    ]


def stream_for_task(
    root_stream: RNGStream,
    label: str,
) -> RNGManifest:
    return root_stream.spawn(label).manifest()
