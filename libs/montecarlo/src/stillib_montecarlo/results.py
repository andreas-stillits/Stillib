from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(slots=True)
class SimulationResult[R]:
    values: Iterable[R]

    @property
    def n_samples(self) -> int:
        return len(self.values)

    @property
    def results(self) -> Iterable[R]:
        return self.values
