from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

import numpy as np
from numpy.typing import npt

from .results import SimulationResult
from .sources import Source


def propagate[R](
    rng: np.random.Generator,
    func: Callable[..., R],
    args: tuple[Source, ...],
    *,
    n_samples: int,
) -> SimulationResult[R]:
    if n_samples < 1:
        raise ValueError("n_samples must be >= 1")

    results: list[R] = []

    for _ in range(n_samples):
        sampled_args = [arg.sample(rng) for arg in args]
        result = func(*sampled_args)
        results.append(result)

    return SimulationResult(results)


def propagate_numpy(
    rng: np.random.Generator,
    func: Callable[..., np.ndarray],
    args: tuple[Source, ...],
    *,
    n_samples: int,
) -> SimulationResult:
    if n_samples < 1:
        raise ValueError("n_samples must be >= 1")

    sampled_args = []

    for arg in args:
        if hasattr(arg, "sample_numpy"):
            try:
                sampled_arg = arg.sample_numpy(rng, n_samples)
            except Exception as exc:
                raise RuntimeError(
                    f"Error during vectorized sampling of argument {arg}: {exc}"
                ) from exc
            sampled_args.append(sampled_arg)
        else:
            raise TypeError(f"Source {arg} does not support vectorized numpy sampling")

    results = func(*sampled_args)
    return SimulationResult(results)
