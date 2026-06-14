"""Bundle the repo-root engine (+ vendored mido) into web/engine.zip for Pyodide.

The repo root is the single source of truth; the zip is a build artifact
(gitignored) that the browser fetches and unpacks into Pyodide's in-memory
filesystem. numpy and pyyaml are provided by Pyodide itself; mido is pure
Python and not in Pyodide, so we vendor it for fully-offline use.

    python tools/build_engine.py        # run from web/
"""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent      # web/tools
WEB = HERE.parent                           # web
REPO = WEB.parent                           # repo root
OUT = WEB / "engine.zip"

MODULES = [
    "music_generator.py", "arrangement.py", "fugue.py", "process.py",
    "melody.py", "logging_config.py",
]
DIRS = ["library"]


def _mido_dir() -> Path:
    import mido
    return Path(mido.__file__).resolve().parent


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)
        for m in MODULES:
            shutil.copy2(REPO / m, stage / m)
        for d in DIRS:
            shutil.copytree(REPO / d, stage / d)
        shutil.copytree(_mido_dir(), stage / "mido",
                        ignore=shutil.ignore_patterns("__pycache__"))

        with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(stage.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    zf.write(path, path.relative_to(stage))
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
