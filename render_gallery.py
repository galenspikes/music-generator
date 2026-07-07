#!/usr/bin/env python3
# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""Render the curated demo highlight set to committable MIDI (site/assets/midi).

Run via ``make gallery``. Renders each song (``songs/*.yml``) and preset
(``library/song_cookbook.py``) in GALLERY to a fresh MIDI file, with no audio
step — the site's player renders MIDI client-side.
"""

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from library.song_cookbook import resolve_recipe  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
SONGS_DIR = SCRIPT_DIR / "songs"
MIDI_DIR = SCRIPT_DIR / "output" / "midi"
GALLERY_DIR = SCRIPT_DIR / "site" / "assets" / "midi"
SEED = 1

# (kind, name) where kind is "song" or "preset"; the output file is <name>.mid.
GALLERY: list[tuple[str, str]] = [
    ("song", "kiss"),
    ("song", "isnt_she_lovely"),
    ("song", "autumn_leaves"),
    ("song", "girl_from_ipanema"),
    ("song", "yesterday"),
    ("song", "riders_on_the_storm"),
    ("song", "whiter_shade_of_pale"),
    ("preset", "dense_colors"),
    ("preset", "counterpoint"),
    ("preset", "bach_prelude"),
    ("preset", "perc_evolution"),
    ("preset", "salsa"),
    ("preset", "rock"),
    ("preset", "rnb"),
]


def render_one(kind: str, name: str) -> Path:
    out_slug = f"_gallery_{name}"
    dest_dir = MIDI_DIR / out_slug
    shutil.rmtree(dest_dir, ignore_errors=True)

    if kind == "song":
        args = ["--song", str(SONGS_DIR / f"{name}.yml")]
    else:
        _slug, payload = resolve_recipe(name)
        args = [str(a) for a in payload.get("args", [])]

    cmd = [sys.executable, str(SCRIPT_DIR / "music_generator.py"), *args,
           "--no-play", "--seed", str(SEED), "--out", out_slug]
    result = subprocess.run(cmd, cwd=str(SCRIPT_DIR), capture_output=True, text=True)
    if result.returncode != 0:
        tail = (result.stderr.strip().splitlines() or ["(no output)"])[-1]
        raise RuntimeError(f"render failed for {name}: {tail}")
    produced = sorted(dest_dir.glob("*.mid"))
    if not produced:
        raise RuntimeError(f"no MIDI produced for {name}")
    return produced[-1]


def main() -> int:
    GALLERY_DIR.mkdir(parents=True, exist_ok=True)
    ok = 0
    for kind, name in GALLERY:
        try:
            produced = render_one(kind, name)
        except Exception as exc:  # noqa: BLE001 — report and keep going
            print(f"FAILED {name}: {exc}")
            continue
        target = GALLERY_DIR / f"{name}.mid"
        shutil.copyfile(produced, target)
        shutil.rmtree(produced.parent, ignore_errors=True)
        print(f"OK {name:22} -> {target.relative_to(SCRIPT_DIR)}")
        ok += 1
    print(f"\nRendered {ok}/{len(GALLERY)} demos to {GALLERY_DIR.relative_to(SCRIPT_DIR)}")
    return 0 if ok == len(GALLERY) else 1


if __name__ == "__main__":
    raise SystemExit(main())
