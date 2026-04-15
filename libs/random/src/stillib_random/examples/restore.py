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
