"""Bridge between the Toga UI and the pure-Python ``music_generator`` engine.

The engine is the repo-root code (the project's crown jewel). To keep a single
source of truth it is *not* duplicated in git: ``tools/sync_engine.py`` vendors
it into ``musicgen/_engine/`` at build time (that directory is gitignored).

At runtime we:
  1. put ``_engine/`` on ``sys.path`` so the engine's top-level imports
     (``import music_generator``, ``import melody`` ...) resolve unchanged;
  2. point the engine at an app-writable output directory via the
     ``MUSICGEN_OUTPUT_DIR`` environment variable the engine honours;
  3. call ``music_generator.main()``, which returns the path to the MIDI file
     it wrote.

No FluidSynth, no ffmpeg, no network — pure-Python MIDI generation on-device.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parent / "_engine"


def _ensure_engine_on_path() -> None:
    path = str(_ENGINE_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)


def _rewrite_library_paths(args: list[str]) -> list[str]:
    """Cookbook presets reference library files as ``library/...`` relative to
    the repo root. On-device the working directory is unspecified, so rewrite
    those tokens to absolute paths inside the vendored engine."""
    rewritten: list[str] = []
    for arg in args:
        if isinstance(arg, str) and arg.startswith("library/"):
            rewritten.append(str(_ENGINE_DIR / arg))
        else:
            rewritten.append(arg)
    return rewritten


def load_presets() -> dict[str, dict]:
    """Return the engine's song cookbook ``{name: {title, description, args}}``.

    Returns an empty dict if the cookbook cannot be imported, so the UI can
    still offer custom generation."""
    _ensure_engine_on_path()
    try:
        from library.song_cookbook import SONG_COOKBOOK  # noqa: E402
    except Exception:  # pragma: no cover - defensive on-device guard
        return {}
    return SONG_COOKBOOK


def generate(args: list[str], *, output_dir: Path | str,
             out_name: str = "song") -> str:
    """Run the engine with CLI-style ``args`` and return the MIDI file path.

    ``output_dir`` must be a writable location (e.g. the app's data dir).
    """
    _ensure_engine_on_path()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    os.environ["MUSICGEN_OUTPUT_DIR"] = str(output_dir)

    import music_generator as mg  # noqa: E402 - imported after path/env setup

    argv = ["music_generator.py", *_rewrite_library_paths(args),
            "--out", out_name, "--no-play"]
    saved_argv = sys.argv
    try:
        sys.argv = argv
        midi_path = mg.main()
    finally:
        sys.argv = saved_argv
    return midi_path
