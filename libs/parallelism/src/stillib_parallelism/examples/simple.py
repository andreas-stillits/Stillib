from __future__ import annotations

import numpy as np
from stillib_parallelism import stream



def execute(x: float) -> float:
    return 2 * x

xs = np.linspace(0, 10, 11)
for y in stream(
    xs,
    execute,
    ordering = "input"):
    print("2 * x = ", y)