from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .results import SimulationResult
from .sources import Source


def propagate[T, R](
    rng: np.random.Generator,
    func: Callable[[T], R],
    args: tuple[Source, ...],
    *,
    n_samples: int,
) -> SimulationResult[R]:
    if n_samples < 1:
        raise ValueError("n_samples must be >= 1")

    results: list[R] = []

    for _ in range(n_samples):
        sampled_args = [arg.sample_once(rng) for arg in args]
        result = func(*sampled_args)
        results.append(result)

    return SimulationResult(results)


def propagate_vectorized[T, R](
    rng: np.random.Generator,
    func: Callable[[T], R],
    args: tuple[Source, ...],
    *,
    n_samples: int,
) -> SimulationResult[R]:
    if n_samples < 1:
        raise ValueError("n_samples must be >= 1")

    if n_samples < 1:
        raise ValueError("n_samples must be >= 1")

    sampled_args = [arg.sample_many(rng, n_samples) for arg in args]
    results = func(*sampled_args)
    return SimulationResult(results)
