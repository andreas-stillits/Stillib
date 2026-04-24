from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import numpy as np
from stillib_parallelism import collect, print_progress


@dataclass
class Task:
    index: int
    x: float


def make_tasks(xmin: float, xmax: float, n: int) -> list[Task]:
    x_values = np.linspace(xmin, xmax, n)
    return [Task(index=i, x=x) for i, x in enumerate(x_values)]


_STATE: dict[str, Any] = {}


def initializer(increment: bool) -> None:
    global _STATE
    _STATE["increment"] = increment


def execute_task(task: Task) -> float:
    increment = _STATE["increment"]
    if increment:
        return task.x + 1
    return task.x


def main() -> int:
    increment = True
    tasks = make_tasks(0, 10, 11)
    report = collect(
        tasks,
        execute_task,
        initializer=initializer,
        initargs=(increment,),
        progress_callback=print_progress,
        ordering="input",
        error_policy="raise",
    )
    print("All tasks completed: ", report.ok)
    summary = {item.index: item.result for item in report.completed}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
