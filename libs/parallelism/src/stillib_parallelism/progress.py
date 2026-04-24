from __future__ import annotations

import sys

from .models import ProgressUpdate


def print_progress(update: ProgressUpdate) -> None:
    """
    Live progress update printer to stdout.
    """
    total = "?" if update.total is None else str(update.total)
    estimated_time_left = None
    if update.total is not None and update.completed > 0:
        time_per_task = update.elapsed_time / update.completed
        estimated_time_left = time_per_task * (update.total - update.completed)

    line = (
        f"submitted: {update.submitted},  "
        f"completed: {update.completed},  "
        f"failed: {update.failures},  "
        f"running: {update.running},  "
        f"total: {total}  "
        f"elapsed: {update.elapsed_time:.2f}s  "
    )
    if estimated_time_left is not None:
        line += f"estimated time left: {estimated_time_left:.2f}s"

    # clear line, return to start, print new status
    sys.stdout.write("\r\033[2K" + line)
    sys.stdout.flush()
    return
