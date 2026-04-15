from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .results import SimulationResult
from .sources import Source, SupportsVectorizedSampling


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

    sampled_args = []

    for arg in args:
        if isinstance(arg, SupportsVectorizedSampling):
            try:
                sampled_arg = arg.sample_numpy(rng, n_samples)
            except Exception as exc:
                raise RuntimeError(
                    f"Error during vectorized sampling of argument {arg}: {exc}"
                ) from exc
            sampled_args.append(sampled_arg)
        else:
            raise TypeError(f"Source {arg} does not support vectorized numpy sampling")
        sampled_args.append(sampled_arg)

    results = func(*sampled_args)
    return SimulationResult(results)
