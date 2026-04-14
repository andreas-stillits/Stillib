from stillib_random import from_seed

root = from_seed(12345)
replicate_streams = root.spawn_many(5, prefix="replicate")

for stream in replicate_streams:
    rng = stream.generator()
    print(stream.label, rng.uniform())
