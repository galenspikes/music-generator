"""Vendor the repo-root engine into ``musicgen/_engine/`` for packaging.

The repo root is the single source of truth for the generation engine; the
vendored copy is gitignored and rebuilt by this script. Run it before every
``briefcase build``/``briefcase run`` (and whenever the engine changes):

    python tools/sync_engine.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent          # ios/tools
IOS = HERE.parent                               # ios
REPO = IOS.parent                               # repo root
DEST = IOS / "src" / "musicgen" / "_engine"

# Pure-Python engine modules the app imports (directly or transitively).
MODULES = [
    "music_generator.py",
    "arrangement.py",
    "fugue.py",
    "process.py",
    "melody.py",
    "logging_config.py",
]
# Data/code directories the engine reads at runtime.
DIRS = ["library"]


def main() -> None:
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    for module in MODULES:
        shutil.copy2(REPO / module, DEST / module)
    for directory in DIRS:
        shutil.copytree(REPO / directory, DEST / directory)
    print(f"Vendored engine -> {DEST.relative_to(IOS)}")


if __name__ == "__main__":
    main()
