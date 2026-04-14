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


def summarize_numeric(result: SimulationResult[float]) -> dict[str, float]:
    values = result.values
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    return {"mean": mean, "variance": variance}
