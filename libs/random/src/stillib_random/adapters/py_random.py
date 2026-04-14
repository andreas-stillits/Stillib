from __future__ import annotations

import random

from ..core import RNGStream


def as_python_random(stream: RNGStream) -> random.Random:
    """Get a Python random.Random from a RNGStream."""
    rng = stream.generator()
    seed = int(rng.integers(0, 2**63, dtype="uint64"))
    return random.Random(seed)
