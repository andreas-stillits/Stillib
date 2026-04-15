from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core import RNGStream
from .manifest import RNGManifest
from .state import RNGCursor, RNGSnapshot


def _snapshot_from_dict(data: dict[str, Any]) -> RNGSnapshot:
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


def save_snapshot(cursor: RNGCursor, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cursor.save_snapshot(path)


def load_snapshot(path: str | Path) -> RNGSnapshot:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
        snapshot = _snapshot_from_dict(data)
        return snapshot
