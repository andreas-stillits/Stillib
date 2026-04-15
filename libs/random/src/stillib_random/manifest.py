from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RNGManifest:
    """A manifest of the RNG state, used for provenance tracking."""

    label: str  # human readable identifier for the RNGStream
    entropy: int | Sequence[int]  # defines the root origin of randomness
    spawn_key: tuple[
        int, ...
    ]  # defines the exact stream in that random universe via an adress, e.g. (0, ), (1, 2, ), etc.
