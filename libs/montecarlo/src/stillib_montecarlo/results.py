from __future__ import annotations

from collections.abc import Iterable, Sized
from dataclasses import dataclass


@dataclass(slots=True)
class SimulationResult[R]:
    values: Iterable[R]

    @property
    def n_samples(self) -> int:
        if isinstance(self.values, Sized):
            return len(self.values)
        else:
            raise ValueError("Cannot determine n_samples for non-sized iterable")

    @property
    def results(self) -> Iterable[R]:
        return self.values
