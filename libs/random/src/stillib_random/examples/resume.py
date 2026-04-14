from stillib_random import from_seed

stream = from_seed(12345).spawn("child")
manifest = stream.manifest()
print(manifest)

same_stream = stream.from_manifest(manifest)
rng = same_stream.generator()
print(same_stream.manifest())
