from __future__ import annotations

import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

import numpy as np

from ._internals import label_to_uint32, normalize_label
from .manifest import RNGManifest
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

    # derive a stream from a seed and provide a label for provenance
    @classmethod
    def from_seed(cls, seed: int, label: str = "root") -> RNGStream:
        label = normalize_label(label)
        return cls(np.random.SeedSequence(seed), label=label)

    # choose a predefined seed instead
    @classmethod
    def from_entropy(cls, label: str = "root") -> RNGStream:
        label = normalize_label(label)
        seed = secrets.randbits(128)
        return cls(np.random.SeedSequence(seed), label=label)

    # reconstruct a stream from a manifest (entropy/seed + spawn_key)
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
        child_index = label_to_uint32(
            label
        )  # derive spawn key number (int) deterministically from the label
        child_seed_sequence = np.random.SeedSequence(
            entropy=self._seed_sequence.entropy,
            spawn_key=(
                *self._seed_sequence.spawn_key,
                child_index,
            ),  # combine parent spawn key and child contribution deterministically
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
        entropy = self._seed_sequence.entropy
        if entropy is None:
            raise ValueError("SeedSequence has no entropy, cannot create manifest")

        entropy = cast(int | Sequence[int], entropy)

        return RNGManifest(
            label=self.label,
            entropy=entropy,
            spawn_key=self._seed_sequence.spawn_key,
        )

    def generator(self) -> np.random.Generator:
        return np.random.default_rng(self._seed_sequence)

    def cursor(self) -> RNGCursor:
        return RNGCursor.from_stream(self)
