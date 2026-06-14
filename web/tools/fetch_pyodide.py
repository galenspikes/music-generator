"""Assemble a minimal self-hosted Pyodide runtime into web/pyodide/.

For a fully-offline PWA we self-host Pyodide rather than load it from a CDN.
We only need the runtime plus the wheels the engine uses (numpy, pyyaml, and
their dep packaging); everything else in the ~300 MB full distribution is
skipped, leaving ~25 MB.

    python tools/fetch_pyodide.py                  # from web/, default CDN
    python tools/fetch_pyodide.py --from-tarball   # use the GitHub release tarball

The result (web/pyodide/) is a build artifact and is gitignored; CI / the
Pages deploy regenerates it.
"""

from __future__ import annotations

import argparse
import io
import sys
import tarfile
import urllib.request
from pathlib import Path

VERSION = "0.26.2"
HERE = Path(__file__).resolve().parent
DEST = HERE.parent / "pyodide"

# Runtime files + the wheels we actually load.
RUNTIME = [
    "pyodide.js", "pyodide.mjs", "pyodide.asm.js", "pyodide.asm.wasm",
    "python_stdlib.zip", "pyodide-lock.json",
]
WHEELS = [
    "numpy-1.26.4-cp312-cp312-pyodide_2024_0_wasm32.whl",
    "PyYAML-6.0.1-cp312-cp312-pyodide_2024_0_wasm32.whl",
    "packaging-23.2-py3-none-any.whl",
    "micropip-0.6.0-py3-none-any.whl",
]
CDN = f"https://cdn.jsdelivr.net/pyodide/v{VERSION}/full/"
TARBALL = (f"https://github.com/pyodide/pyodide/releases/download/"
           f"{VERSION}/pyodide-{VERSION}.tar.bz2")


def from_cdn() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    for name in RUNTIME + WHEELS:
        url = CDN + name
        print(f"  {url}")
        urllib.request.urlretrieve(url, DEST / name)


def from_tarball() -> None:
    print(f"Downloading {TARBALL} (~300 MB)…")
    data = urllib.request.urlopen(TARBALL).read()
    wanted = set(RUNTIME + WHEELS)
    DEST.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:bz2") as tf:
        for member in tf.getmembers():
            base = Path(member.name).name
            if base in wanted:
                src = tf.extractfile(member)
                if src is not None:
                    (DEST / base).write_bytes(src.read())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from-tarball", action="store_true",
                    help="fetch from the GitHub release tarball instead of the CDN")
    args = ap.parse_args()
    (from_tarball if args.from_tarball else from_cdn)()
    have = sorted(p.name for p in DEST.glob("*"))
    print(f"Assembled {DEST} with {len(have)} files.")
    missing = set(RUNTIME + WHEELS) - set(have)
    if missing:
        print("MISSING:", ", ".join(sorted(missing)), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
