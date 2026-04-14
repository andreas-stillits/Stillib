from __future__ import annotations

import secrets
from dataclasses import dataclass

import numpy as np

from ._internals import label_to_uint32, normalize_label
from .provenance import RNGManifest
from .state import RNGCursor


@dataclass(frozen=True, slots=True)
class RNGStream:
    """
    Where does the stream come from?
    What child streams can it derive?
    How do I reconstruct the same stream elsewhere?
    """

    _seed_sequence: np.random.SeedSequence
    label: str = "root"

    # classmethods recieve the class itself instead of an instance of it
    # in that sense this is a factory for creating an instance in different ways
    @classmethod
    def from_seed(cls, seed: int, label: str = "root") -> RNGStream:
        label = normalize_label(label)
        return cls(np.random.SeedSequence(seed), label=label)

    @classmethod
    def from_entropy(cls, label: str = "root") -> RNGStream:
        label = normalize_label(label)
        seed = secrets.randbits(128)
        return cls(np.random.SeedSequence(seed), label=label)

    @classmethod
    def from_manifest(cls, manifest: RNGManifest) -> RNGStream:
        return cls(
            np.random.SeedSequence(
                entropy=manifest.entropy,
                spawn_key=manifest.spawn_key,
            ),
            label=manifest.label,
        )

    def spawn(self, label: str) -> RNGStream:
        label = normalize_label(label)
        child_index = label_to_uint32(label)
        child_seed_sequence = np.random.SeedSequence(
            entropy=self._seed_sequence.entropy,
            spawn_key=(*self._seed_sequence.spawn_key, child_index),
        )
        return RNGStream(child_seed_sequence, label=label)

    def spawn_many(self, n: int, prefix: str = "child") -> list[RNGStream]:
        if n < 1:
            raise ValueError("n must be a positive integer")

        prefix = normalize_label(prefix)
        children = self._seed_sequence.spawn(n)

        return [
            RNGStream(child, label=f"{prefix}-{i}") for i, child in enumerate(children)
        ]

    def manifest(self) -> RNGManifest:
        return RNGManifest(
            label=self.label,
            entropy=self._seed_sequence.entropy,
            spawn_key=self._seed_sequence.spawn_key,
        )

    def generator(self) -> np.random.Generator:
        return np.random.default_rng(self._seed_sequence)

    def cursor(self) -> RNGCursor:
        return RNGCursor.from_stream(self)
