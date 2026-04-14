from __future__ import annotations

import hashlib


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
