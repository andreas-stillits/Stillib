from time import perf_counter

import numpy as np
import stillib_montecarlo as mc
import stillib_random as r


def func(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
    return x + y + z


def z_custom(rng: np.random.Generator) -> float:
    while True:
        draw = rng.normal(0, 1)
        if (
            abs(draw) < 2
        ):  # simple rejection sampling to keep values within a reasonable range
            return draw


def z_custom_numpy(rng: np.random.Generator, n: int) -> np.ndarray:
    draws = []
    while len(draws) < n:
        draw = rng.normal(0, 1)
        if (
            abs(draw) < 2
        ):  # simple rejection sampling to keep values within a reasonable range
            draws.append(draw)
    return np.array(draws)


root = r.from_seed(12345)
cursor = root.cursor()
rng = cursor.generator()

snapshot = cursor.snapshot()

x = mc.Constant(10)
y = mc.Empirical([1, 2, 3])
z_single = mc.Model.single(lambda rng: z_custom(rng))
z_numpy = mc.Model.numpy(lambda rng, n: z_custom_numpy(rng, n))

t0 = perf_counter()

result1 = mc.propagate(
    rng,
    func,
    (x, y, z_single),
    n_samples=10000,
).results

t1 = perf_counter()

result2 = mc.propagate_numpy(
    rng,
    func,
    (x, y, z_numpy),
    n_samples=10000,
).results

t2 = perf_counter()

print("Time for single sampling:", t1 - t0)
print("Time for vectorized sampling:", t2 - t1)
