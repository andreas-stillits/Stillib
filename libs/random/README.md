
# Stream: reproducible source identity 

# Cursor: mutable generator state

# Multiprocessing:
    - never pass a live generator; pass a manifest and reconstruct it --> avoid state changes
    - each task has its own stream --> worker and order independence