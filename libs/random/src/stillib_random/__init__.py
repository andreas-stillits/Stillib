from .core import RNGStream
from .provenance import RNGManifest


def from_seed(seed: int, label: str = "root") -> RNGStream:
    return RNGStream.from_seed(seed, label)


def from_entropy(label: str = "root") -> RNGStream:
    return RNGStream.from_entropy(label)


__all__ = [
    "RNGManifest",
    "RNGStream",
    "from_entropy",
    "from_seed",
]
