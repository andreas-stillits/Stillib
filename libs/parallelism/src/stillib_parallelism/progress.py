from __future__ import annotations

import sys

from .models import ProgressUpdate


def print_progress(update: ProgressUpdate) -> None:
    """
    Live progress update printer to stdout.
    """
    total = "?" if update.total is None else str(update.total)
    line = (
        f"submitted: {update.submitted},  "
        f"completed: {update.completed},  "
        f"failed: {update.failures},  "
        f"running: {update.running},  "
        f"total: {total}   "
        f"elapsed: {update.elapsed_time:.2f}s  "
    )

    # clear line, return to start, print new status
    sys.stdout.write("\r\033[2K" + line)
    sys.stdout.flush()
    return
