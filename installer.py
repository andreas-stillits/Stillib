from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
LIBS_DIR = REPO_ROOT / "libs"

KNOWN_LIBS = {
    "montecarlo": LIBS_DIR / "montecarlo",
    "parallelism": LIBS_DIR / "parallelism",
    "paths": LIBS_DIR / "paths",
    "plotting": LIBS_DIR / "plotting",
    "random": LIBS_DIR / "random",
}


def install_lib(name: str) -> None:
    try:
        project_dir = KNOWN_LIBS[name]
    except KeyError as exc:
        known_libs = ", ".join(sorted(KNOWN_LIBS))
        raise SystemExit(
            f"Unknown library '{name}'. Known libraries: {known_libs}"
        ) from exc

    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        raise SystemExit(
            f"Library '{name}' does not have a pyproject.toml file at {pyproject}"
        )

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-e",
        str(project_dir),
    ]

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        known_libs = ", ".join(sorted(KNOWN_LIBS))
        raise SystemExit(
            f"Usage: python installer.py <library_name>\nKnown libraries: {known_libs}"
        )

    name: str = argv[1]

    if name == "all":
        for lib in KNOWN_LIBS:
            install_lib(lib)
    else:
        install_lib(argv[1])

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
