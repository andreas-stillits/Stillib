from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from .api import collect_parallel, stream_parallel
from .models import ProgressUpdate


@dataclass(frozen=True)
class Task:
    x: int


def init_worker() -> None:
    # Put one-time worker setup here if needed.
    # Example: set BLAS thread limits, load a model, etc.
    pass


def execute_task(task: Task) -> float:
    if task.x == 13:
        raise ValueError("bad luck")
    return sqrt(task.x)


def make_tasks():
    for i in range(30):
        yield Task(i)


def on_progress(update: ProgressUpdate) -> None:
    print(
        f"submitted={update.submitted} "
        f"completed={update.completed} "
        f"failed={update.failed} "
        f"running={update.running} "
        f"elapsed={update.duration:.2f}s"
    )


# 1) Fail-fast streaming
for result in stream_parallel(
    make_tasks(),
    execute_task,
    max_workers=4,
    ordering="completion",
    batch_size=4,
    buffersize=8,
    initializer=init_worker,
    init_args=(),
    progress_callback=on_progress,
    interrupt_policy="cancel",
):
    print(result)


# 2) Collecting run
report = collect_parallel(
    make_tasks(),
    execute_task,
    max_workers=4,
    ordering="input",
    batch_size=4,
    buffersize=8,
    initializer=init_worker,
    init_args=(),
    error_policy="collect",
    progress_callback=on_progress,
    task_namer=lambda task: f"x={task.x}",
    interrupt_policy="drain",
)

print("ok:", report.ok)
print("results:", report.results)
print("n_failures:", len(report.failures))
if report.failures:
    print(report.failures[0].traceback)
