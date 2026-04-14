from __future__ import annotations

import shutil

from stillib_random import from_seed, from_snapshot, load_snapshot, save_snapshot

root = from_seed(1234, label="root")
cursor = root.cursor()
rng = cursor.generator

print(rng.integers(0, 10, size=5))

path = "tmp/snapshot.json"

save_snapshot(cursor, path)
snapshot = load_snapshot(path)

print(
    rng.integers(0, 10, size=5)
)  # this will continue the sequence from the original cursor

cursor = from_snapshot(snapshot)
rng = cursor.generator
print("reloaded origin: ", cursor.stream_manifest.label)
print(rng.integers(0, 10, size=5))

# delete the tmp/ directory after the test
shutil.rmtree("tmp")
