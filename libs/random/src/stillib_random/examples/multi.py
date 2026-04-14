from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

from stillib_random import RNGStream, from_seed
from stillib_random.multiprocessing import assign_streams


@dataclass(frozen=True)
class Task:
    x: float


def execute_task(task: Task, manifest) -> float:
    stream = RNGStream.from_manifest(manifest)
    rng = stream.generator()
    noise = rng.normal(loc=0.0, scale=1.0)
    return task.x + noise


def worker(payload):
    task, manifest = payload
    return execute_task(task, manifest)


tasks = [Task(x) for x in range(10)]
root = from_seed(42, label="experiment")
assigned = assign_streams(tasks, root)

payloads = [(item.task, item.manifest) for item in assigned]

with ProcessPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(worker, payloads))


for result in results:
    print(result)
