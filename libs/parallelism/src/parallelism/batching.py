from __future__ import annotations

from collections.abc import Iterable, Iterator

from .models import InputType


def chunked(
    tasks: Iterable[InputType],
    batch_size: int,
) -> Iterator[list[InputType]]:
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    batch: list[InputType] = []
    for task in tasks:
        batch.append(task)

        # if at the desired size, send it off and reset container
        if len(batch) >= batch_size:
            yield batch
            batch = []

    # if final didnt reach batch size, send it off anyway
    if batch:
        yield batch
