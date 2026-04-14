from __future__ import annotations

import hashlib
from typing import Any

import numpy as np


def normalize_label(label: str) -> str:
    label = label.strip().lower()
    if not label:
        raise ValueError("label must be a non-empty string")
    return label


def label_to_uint32(label: str) -> int:
    """
    Deterministically map a label to a uint32 integer.
    Used to derive stable semantic children streams
    """
    digest = hashlib.blake2b(label.encode("utf-8"), digest_size=8).digest()
    value = int.from_bytes(digest, byteorder="big", signed=False)
    return value % (2**32)


def _map_for_json(obj: Any) -> Any:
    """Recursively map objects to JSON-serializable types."""
    if isinstance(obj, dict):
        return {str(k): _map_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_map_for_json(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    return obj
