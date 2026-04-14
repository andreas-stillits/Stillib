from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RNGManifest:
    """A manifest of the RNG state, used for provenance tracking."""

    label: str
    entropy: int | tuple[int, ...]
    spawn_key: tuple[int, ...]
