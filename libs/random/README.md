# stillib-random

Managed RNGs with deterministic spawning, multiprocessing and store/resume support.

## Why this exists

It is important in a scientific context to facilitate reproducibility, even when random processes are involved. It is common to just declare a global seed or at best manage multiple seeds ad-hoc. This library streamlines the processes of:
- Defining an RNG Stream
- Deterministically spawn substreams from a parent
- Reconstruction of a random state
- Store/Resume support with optional serialization to disk

## Installation

From Stillib project root, run:

```bash
python installer.py random
```

## Minimal Example

```python 
from stillib_random import from_seed

root = from_seed(12345, label="experiment") # define a root stream
noise_stream = root.spawn("noise") # spawn a substream from a label
rng = noise_stream.generator() # extract its np.random.Generator

n_samples: int = 1_000
dx = rng.normal(0.0, 1.0, size=n_samples) # pull random numbers from the RNG

```

## Core Concepts and Abstractions

### RNGStream

This object models an RNG stream. A stream  is the origin of a random sequence of numbers, where the generator keeps track of "the next number". In that sense the stream is immutable and the generator represents the changing state. A RNGStream answers:
- Where does the stream come from?
- What child streams can it derive?
- How do I reconstruct the same stream elsewhere? 


### RNGManifest

This object carries the information to reconstruct a stream in a certain state.
Instead of passing around mutable generators, one should pass a manifest and resconstruct the stream and its generator when needed.
It is immutable after creation.


### RNGCursor

This object is a mutable tracker of the RNG state. It carries the stream manifest and the stream generator. It can produce an RNGSnapshot of the current state and later restore the state from it.
RNGCursor answers:
- What is the current generator state?
- How do I save and restore mid-run?
- How do I continue exactly where I left off?


### RNGSnapshot

This object carries the information needed to identify the stream and reconstruct the generator state. We can only resume correctly if we know both the stream and the generator state. It exposes a .to_dict() method for saving to disk as a snapshot.json.


## Main API 

- from_entropy(label) -> RNGStream     (creates a highly random seed, new every call)
- from_seed(seed, label) -> RNGStream  (manually assigned seed)
- RNGStream.generator() -> np.random.Generator
- RNGStream.spawn(label) -> RNGStream
- RNGStream.spawn_many(n, prefix) -> list[RNGStream]
- RNGStream.manifest() -> RNGManifest
- RNGStream.from_manifest(RNGManifest) -> RNGStream
- RNGStream.cursor() -> RNGCursor[RNGManifest, Generator]
- save_snapshot(RNGCursor, path) -> None
- load_snapshot(path) -> RNGSnapshot
- from_snapshot(RNGSnapshot) -> RNGCursor


## Design Choices

This library is designed to:
- Wrap np.random.Generator in a simple API
- Make it easy to manage streams and generator states
- Provide ergonomics for multiprocessing and pause/resume computation
- Discourage global seed/state dependence

It does not try to:
- Invent new generators
- Provide out of the bow statistical tests

## Contracts, Pitfalls, and Notes

Notice that different operations although superficially equaivalent may yield different outcomes. For example:
- Repeatedly spawning N child streams with RNGStream.spawn() will not yield the same states as calling RNGStream.spawn_many(N). 
- Repeatedly sampling an RNG like: rng.normal(0, 1) will not yield the same sequence of numbers as: rng.normal(0, 1, size=N)

However, creating a snapshot, drawing N values, reconstructing the saved state and drawing N values in the same way must yield the same sequence.

- Be aware that .spawn() derives the child identity from the passed label, where spawn_many() derives it deterministically from the parent regardless of the assigned label. 
This was preferred to avoid dependence on a label-scheme and lose later repreducibility if labels were to change or be lost. The identity is instead fully tied to the index.


## More Examples

### Multiprocessing
This example shows how to easily manage task specific streams for independent tasks run in parallel.

```python 
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
```

### Restoring State
This example shows the use of RNGCursor and RNGSnapshot for recreating a specific RNG state.

```python 
from __future__ import annotations

from stillib_random import from_seed

stream = from_seed(123, label="chain-0")
cursor = stream.cursor()

x1 = cursor.generator().normal(size=5)
snapshot = cursor.snapshot()
x2 = cursor.generator().normal(size=5)

restored = type(cursor).from_snapshot(snapshot)
x3 = restored.generator().normal(size=5)

print(f"x1: {x1}")
print(f"x2: {x2}")
print(f"x3: {x3}")
print(f"Are x2 and x3 equal? {(x2 == x3).all()}")

```
