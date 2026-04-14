from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol

import numpy as np


class Source[T]:
    def sample_once(self, rng: np.random.Generator) -> T:
        raise NotImplementedError

    def sample_many(self, rng: np.random.Generator, n_samples: int):
        if n_samples < 1:
            raise ValueError("n_samples must be >= 1")
        return [self.sample_once(rng) for _ in range(n_samples)]


@dataclass(frozen=True, slots=True)
class Constant[T](Source[T]):
    value: T

    def sample_once(self, rng: np.random.Generator) -> T:
        return self.value

    def sample_many(self, rng: np.random.Generator, n_samples: int):
        if n_samples < 1:
            raise ValueError("n_samples must be >= 1")

        # broadcast if numpy
        if isinstance(self.value, np.ndarray):
            return np.broadcast_to(self.value, (n_samples,) + self.value.shape)
        else:
            return [self.value] * n_samples


@dataclass(frozen=True, slots=True)
class Empirical[T](Source[T]):
    values: tuple[T, ...]

    # Accept an Iterable but map to tuple for internal use
    def __init__(self, values: Iterable[T]) -> None:
        values = tuple(values)
        if not values:
            raise ValueError("Empirical distribution must have at least one value.")
        object.__setattr__(self, "values", values)

    def sample_once(self, rng: np.random.Generator) -> T:
        return rng.choice(self.values, replace=True)

    def sample_many(self, rng: np.random.Generator, n_samples: int):
        if n_samples < 1:
            raise ValueError("n_samples must be >= 1")

        try:
            return rng.choice(self.values, size=n_samples, replace=True)
        except Exception:
            # Fallback to sampling one by one if values are not compatible with vectorized choice
            return [self.sample_once(rng) for _ in range(n_samples)]


@dataclass(frozen=True, slots=True)
class Model[T](Source[T]):
    draw_once: Callable[[np.random.Generator], T]
    draw_many: Callable[[np.random.Generator, int], object] | None = None

    def sample_once(self, rng: np.random.Generator) -> T:
        return self.draw_once(rng)

    def sample_many(self, rng: np.random.Generator, n_samples: int):
        if n_samples < 1:
            raise ValueError("n_samples must be >= 1")

        # if the user provided a vectorized draw function, use it
        if self.draw_many is not None:
            try:
                return self.draw_many(rng, n_samples)
            except Exception:
                pass

        # Fallback to one-by-one sampling for downstream vectorization
        return [self.sample_once(rng) for _ in range(n_samples)]


def constant[T](value: T) -> Constant[T]:
    return Constant(value)


def empirical[T](values: Iterable[T]) -> Empirical[T]:
    return Empirical(values)


def model[T](
    draw_once: Callable[[np.random.Generator], T],
    draw_many: Callable[[np.random.Generator, int], object] | None = None,
) -> Model[T]:
    return Model(draw_once, draw_many)
