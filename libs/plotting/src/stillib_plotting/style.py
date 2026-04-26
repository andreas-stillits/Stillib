from __future__ import annotations

from typing import Any

import matplotlib as mpl

from .colors import CYCLE

_DEFAULT_RCPARAMS = {
    "figure.dpi": 120,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "mathtext.fontset": "stix",
    "font.family": "STIXGeneral",
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "axes.spines.top": False,
    "axes.spines.right": True,
    "axes.linewidth": 0.8,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "lines.linewidth": 1.5,
    "lines.markersize": 4,
    "legend.frameon": False,
    "axes.prop_cycle": mpl.cycler(color=CYCLE),
}


def use_style(overrides: dict[str, Any] | None = None) -> None:
    mpl.rcParams.update(_DEFAULT_RCPARAMS)
    if overrides:
        mpl.rcParams.update(overrides)
    return


def reset_style() -> None:
    mpl.rcdefaults()
    return
