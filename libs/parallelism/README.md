# utility library for process and thread parallelism in python


# IDEAS FOR FUTURE ADDITIONS


First addition: progress callback

This is a very clean next step because it does not change the architecture. It just adds reporting around:

submitted
completed
failed
running
elapsed time


Second addition: input-order mode

Right now results come in completion order. Input-order mode is the next clean extension.

It is however easy if in collect mode to post sort:

$$
completed = report.completed
completed.sort(key = lambda item: item.index)
results = [item.result for item in completed]
$$



Third addition: Ctrl+C policy

The current version is missing clean up in _engine._iter_outcomes().