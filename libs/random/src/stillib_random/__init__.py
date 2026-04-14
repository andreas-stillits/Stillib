from .core import RNGStream
from .provenance import RNGManifest
from .state import RNGCursor, RNGSnapshot, load_snapshot, save_snapshot


def from_seed(seed: int, label: str = "root") -> RNGStream:
    return RNGStream.from_seed(seed, label)


def from_entropy(label: str = "root") -> RNGStream:
    return RNGStream.from_entropy(label)


def from_snapshot(snapshot: RNGSnapshot) -> RNGCursor:
    return RNGCursor.from_snapshot(snapshot)


__all__ = [
    "RNGManifest",
    "RNGSnapshot",
    "RNGCursor",
    "RNGStream",
    "from_entropy",
    "from_seed",
    "from_snapshot",
    "load_snapshot",
    "save_snapshot",
]
