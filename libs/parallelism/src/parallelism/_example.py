from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np

from .api import collect, stream
from .models import ProgressUpdate


@dataclass(frozen=True)
class Task:
    x: int


_STATE: dict[str, object] = {}
# state will be worker-specific when using multiprocessing,
#   so safe to use global mutable state


def init_worker(model_path: str, calibration_path: str) -> None:
    _STATE["model"] = np.loadtxt(model_path)
    _STATE["calibration"] = np.load(calibration_path)
    return


def execute_task(task: Task) -> float:
    model = _STATE["model"]
    calibration = _STATE["calibration"]
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
        f"elapsed={update.elapsed_time:.2f}s"
    )


# 1) Fail-fast streaming
for result in stream(
    make_tasks(),
    execute_task,
    max_workers=4,
    buffersize=8,
    initializer=init_worker,
    initargs=(),
    progress_callback=on_progress,
):
    print(result)


# 2) Collecting run
report = collect(
    make_tasks(),
    execute_task,
    max_workers=4,
    buffersize=8,
    initializer=init_worker,
    initargs=(),
    progress_callback=on_progress,
    task_namer=lambda task: f"x={task.x}",
)

print("ok:", report.ok)
print("results:", report.results)
print("n_failures:", len(report.failed))
if report.failed:
    print(report.failed[0].traceback)
