from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from ._internals import _map_for_json
from .manifest import RNGManifest

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest": _map_for_json(asdict(self.manifest)),
            "bit_generator_name": self.bit_generator_name,
            "bit_generator_state": _map_for_json(self.bit_generator_state),
        }


def snapshot_from_dict(data: dict[str, Any]) -> RNGSnapshot:
    if "manifest" not in data:
        raise ValueError("Missing 'manifest' in snapshot data")
    if "bit_generator_name" not in data:
        raise ValueError("Missing 'bit_generator_name' in snapshot data")
    if "bit_generator_state" not in data:
        raise ValueError("Missing 'bit_generator_state' in snapshot data")

    return RNGSnapshot(
        manifest=RNGManifest(**data["manifest"]),
        bit_generator_name=data["bit_generator_name"],
        bit_generator_state=data["bit_generator_state"],
    )


@dataclass(slots=True)
class RNGCursor:
    """
    What is the current generator state?
    How do I save and restore mid-run?
    How do I continue exactly where I left off?
    """

    stream_manifest: RNGManifest  # stream identity
    stream_generator: np.random.Generator  # the current state of the generator

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
        try:
            bit_generator_cls = getattr(np.random, snapshot.bit_generator_name)
        except AttributeError as exc:
            raise ValueError(
                f"Unknown bit generator: {snapshot.bit_generator_name}"
            ) from exc
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

    def generator(self) -> np.random.Generator:
        return self.stream_generator

    # save the current state of the generator in a snapshot, which can be used to restore the generator later
    def snapshot(
        self,
    ) -> RNGSnapshot:
        bit_generator = self.stream_generator.bit_generator
        return RNGSnapshot(
            self.stream_manifest,
            type(bit_generator).__name__,
            copy.deepcopy(dict(bit_generator.state)),
        )

    def save_snapshot(self, path: Path) -> None:
        with path.open("w", encoding="utf-8") as f:
            snapshot = self.snapshot()
            f.write(json.dumps(snapshot.to_dict(), indent=4))


def save_snapshot(cursor: RNGCursor, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cursor.save_snapshot(path)


def load_snapshot(path: str | Path) -> RNGSnapshot:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
        snapshot = snapshot_from_dict(data)
        return snapshot
