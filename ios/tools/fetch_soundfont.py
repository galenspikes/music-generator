"""Download a higher-quality General MIDI SoundFont for playback (optional).

The app already bundles a tiny default GM font (``resources/default_gm.sf2``).
This fetches a fuller font and installs it as ``resources/soundfont.sf2``, which
the app prefers over the default. The downloaded font is gitignored (large
binary) — it ships in the built app, not in the repo.

    python tools/fetch_soundfont.py            # default: FluidR3 GM (~140 MB)
    python tools/fetch_soundfont.py --url URL  # any other .sf2

AVMIDIPlayer needs an uncompressed SoundFont (.sf2) or DLS bank — not .sf3.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent          # ios/tools
RESOURCES = HERE.parent / "src" / "musicgen" / "resources"
DEST = RESOURCES / "soundfont.sf2"

# A full, freely-redistributable GM font. ~140 MB — fuller than the bundled
# default; mind the resulting app size.
DEFAULT_URL = (
    "https://github.com/urish/cinto/raw/master/media/FluidR3%20GM.sf2"
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default=DEFAULT_URL, help="SoundFont .sf2 URL")
    args = ap.parse_args()

    RESOURCES.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {args.url}\n  -> {DEST}")
    urllib.request.urlretrieve(args.url, DEST)

    head = DEST.read_bytes()[:12]
    if head[:4] != b"RIFF" or head[8:12] != b"sfbk":
        DEST.unlink(missing_ok=True)
        print("ERROR: downloaded file is not a valid .sf2 SoundFont.",
              file=sys.stderr)
        return 1
    print(f"OK: {DEST.stat().st_size:,} bytes. The app will use it over the "
          "bundled default.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
