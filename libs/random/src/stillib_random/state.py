from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from .provenance import RNGManifest

if TYPE_CHECKING:
    from .core import RNGStream


@dataclass(frozen=True, slots=True)
class RNGSnapshot:
    """
    What is stream identity?
    What does it take to reconstruct a generator?
    """

    manifest: RNGManifest
    bit_generator_name: str  # attribute name of the genertor in np.random
    bit_generator_state: dict[str, Any]  # the state of the generator


@dataclass(slots=True)
class RNGCursor:
    """
    What is the current generator state?
    How do I save and restore mid-run?
    How do I continue exactly where I left off?
    """

    stream_manifest: RNGManifest  # stream identity
    generator: np.random.Generator  # the current state of the generator

    @classmethod
    def from_stream(cls, stream: RNGStream) -> RNGCursor:
        # simply construct
        return cls(
            stream.manifest(),
            stream.generator(),
        )

    @classmethod
    def from_snapshot(cls, snapshot: RNGSnapshot) -> RNGCursor:
        # get the generator class from its name saved in snapshot
        bit_generator_cls = getattr(np.random, snapshot.bit_generator_name)
        # instanciate a new generator
        bit_generator = bit_generator_cls()
        # assign the generator state as saved in snapshot
        bit_generator.state = copy.deepcopy(snapshot.bit_generator_state)
        # create a new RNGCursor with the manifest and the restored generator
        generator = np.random.Generator(bit_generator)
        return cls(
            snapshot.manifest,
            generator,
        )

    # save the current state of the generator in a snapshot, which can be used to restore the generator later
    def snapshot(
        self,
    ) -> RNGSnapshot:
        bit_generator = self.generator.bit_generator
        return RNGSnapshot(
            self.stream_manifest,
            type(bit_generator).__name__,
            copy.deepcopy(bit_generator.state),
        )
