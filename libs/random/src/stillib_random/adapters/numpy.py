from __future__ import annotations

import numpy as np

from ..core import RNGStream
from ..state import RNGCursor


def as_numpy_generator(stream: RNGStream) -> np.random.Generator:
    """Get a numpy Generator from a RNGStream."""
    return stream.generator


def cursor_as_numpy_generator(cursor: RNGCursor) -> np.random.Generator:
    """Get a numpy Generator from a RNGCursor."""
    return cursor.generator
