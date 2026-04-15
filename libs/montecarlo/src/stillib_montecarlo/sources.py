from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import numpy as np


class Source[T]:
    def sample(self, rng: np.random.Generator) -> T:
        raise NotImplementedError

    def sample_numpy(self, rng: np.random.Generator, n_samples: int) -> np.ndarray:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class Constant[T](Source[T]):
    value: T
    numpy_cast: Callable[[T], np.ndarray] | None = None

    def sample(self, rng: np.random.Generator) -> T:
        return self.value

    def sample_numpy(self, rng: np.random.Generator, n_samples: int) -> np.ndarray:
        if n_samples < 1:
            raise ValueError("n_samples must be >= 1")
        if self.numpy_cast is None:  # if no custom casting provided
            arr = np.asarray(self.value)  # wrap in array for broadcasting
        else:
            arr = self.numpy_cast(self.value)  # apply custom casting if provided
        return np.broadcast_to(
            arr, (n_samples, *arr.shape)
        )  # cast to correct shape where axis 0 is the sample axis


@dataclass(frozen=True, slots=True)
class Empirical[T](Source[T]):
    values: tuple[T, ...]
    numpy_cast: Callable[[tuple[T, ...]], np.ndarray] | None = None

    # Accept any iterable but store as a tuple for immutability and consistency
    def __init__(
        self,
        values: Iterable[T],
        numpy_cast: Callable[[tuple[T, ...]], np.ndarray] | None = None,
    ) -> None:
        values = tuple(values)
        if not values:
            raise ValueError("Empirical source must have at least one value.")
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "numpy_cast", numpy_cast)

    def sample(self, rng: np.random.Generator) -> T:
        idx = int(rng.integers(0, len(self.values)))
        return self.values[idx]

    def sample_numpy(self, rng: np.random.Generator, n_samples: int) -> np.ndarray:
        if n_samples < 1:
            raise ValueError("n_samples must be >= 1")

        if self.numpy_cast is None:  # if no custom casting provided
            arr = np.asarray(self.values)  # wrap in array for vectorized indexing
        else:
            arr = self.numpy_cast(self.values)  # apply custom casting if provided

        # verify that the first axis is used for sampling
        if arr.shape[0] != len(self.values):
            raise ValueError(
                "numpy_cast must return an array where the first dimension matches the number of values."
            )

        idxs = rng.integers(0, len(self.values), size=n_samples)
        return arr[idxs]


@dataclass(frozen=True, slots=True)
class Model[T](Source[T]):
    draw: Callable[[np.random.Generator], T] | None = None
    draw_numpy: Callable[[np.random.Generator, int], np.ndarray] | None = None

    @classmethod
    def single(cls, draw: Callable[[np.random.Generator], T]) -> Model[T]:
        return cls(draw=draw, draw_numpy=None)

    @classmethod
    def numpy(
        cls, draw_numpy: Callable[[np.random.Generator, int], np.ndarray]
    ) -> Model[T]:
        return cls(draw=None, draw_numpy=draw_numpy)

    def sample(self, rng: np.random.Generator) -> T:
        if self.draw is None:
            raise NotImplementedError(
                "draw function is not implemented for this Model."
            )
        return self.draw(rng)

    def sample_numpy(self, rng: np.random.Generator, n_samples: int) -> np.ndarray:
        if n_samples < 1:
            raise ValueError("n_samples must be >= 1")
        if self.draw_numpy is not None:
            return self.draw_numpy(rng, n_samples)
        assert self.draw is not None, (
            "At least one of draw or draw_numpy must be implemented."
        )
        # fallback to single sampling if vectorized version is not provided
        return np.stack([np.asarray(self.draw(rng)) for _ in range(n_samples)], axis=0)
