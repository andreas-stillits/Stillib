from stillib_random import from_seed

root = from_seed(12345)
measurement_noise = root.spawn("measurement-noise")

# print(measurement_noise)
# print(measurement_noise.manifest())

rng = measurement_noise.generator()
samples = rng.normal(loc=0, scale=1, size=10_000)

# print(samples.mean(), samples.std())
