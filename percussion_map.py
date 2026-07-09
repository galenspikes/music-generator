# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""The active drum map: letter → GM note number.

Owns loading a drum map from a percussion-library JSON
(``library/percussion_library.json`` by default, with a hardcoded GM
fallback) and the process-global *active* map that token parsing defaults
to. Depends only on :mod:`mtheory`. Part of the :mod:`percussion` package
of modules — import through :mod:`percussion` unless you specifically want
this layer.
"""
import json
import threading
from pathlib import Path

from mtheory import LIB_DIR

__all__ = [
    "DEFAULT_PERC_LIB",
    "FALLBACK_DRUM_MAP",
    "load_drum_map_from",
    "set_active_drum_map",
    "get_drum_map",
]

DEFAULT_PERC_LIB = LIB_DIR / "percussion_library.json"

FALLBACK_DRUM_MAP = {
    # Kicks / snares
    "a": 35,  # Acoustic Bass Drum
    "b": 36,  # Bass Drum 1
    "c": 38,  # Acoustic Snare
    "d": 40,  # Electric Snare
    "e": 37,  # Side Stick / Rimshot
    "f": 39,  # Hand Clap

    # Hi-hats
    "g": 42,  # Closed Hi-Hat
    "h": 44,  # Pedal Hi-Hat
    "i": 46,  # Open Hi-Hat

    # Cymbals
    "j": 49,  # Crash Cymbal 1
    "k": 51,  # Ride Cymbal 1
    "l": 53,  # Ride Bell
    "m": 57,  # Crash Cymbal 2
    "n": 59,  # Ride Cymbal 2
    "o": 55,  # Splash Cymbal
    "p": 52,  # Chinese Cymbal

    # Toms
    "q": 41,  # Low Floor Tom
    "s": 45,  # Low Tom
    "t": 47,  # Low-Mid Tom
    "u": 48,  # Hi-Mid Tom
    "v": 50,  # High Tom

    # Percussion / toys
    "w": 54,  # Tambourine
    "x": 56,  # Cowbell
    "y": 69,  # Cabasa
    "z": 70,  # Maracas
}

# The process-global *active* drum map: a convenience default for the CLI
# and one-off scripts. Concurrent embedders (the web API) should prefer
# loading a map per request via load_drum_map_from() and passing it down
# explicitly (parse_pattern(..., drum_map=...), build_perc_from_args(...,
# drum_map=...)) instead of mutating this global.
_DRUM_MAP_CACHE: dict[str, int] | None = None
_DRUM_MAP_LOCK = threading.Lock()


def load_drum_map_from(path: Path | None) -> dict[str, int]:
    mapping = FALLBACK_DRUM_MAP.copy()
    if path is None:
        return mapping
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return mapping
    except Exception:
        return mapping

    payload = data.get("drum_map")
    if isinstance(payload, dict):
        parsed: dict[str, int] = {}
        for raw_key, raw_val in payload.items():
            key = str(raw_key).strip().lower()
            if not key:
                continue
            note_val = raw_val.get("note") if isinstance(raw_val, dict) else raw_val
            try:
                note_int = int(note_val)
            except (TypeError, ValueError):
                continue
            parsed[key] = note_int
        if parsed:
            mapping.update(parsed)
    return mapping


def set_active_drum_map(source: str | Path | None) -> dict[str, int]:
    path = Path(source) if source is not None else DEFAULT_PERC_LIB
    mapping = load_drum_map_from(path)
    global _DRUM_MAP_CACHE
    with _DRUM_MAP_LOCK:
        _DRUM_MAP_CACHE = mapping
    return mapping


def get_drum_map() -> dict[str, int]:
    with _DRUM_MAP_LOCK:
        mapping = _DRUM_MAP_CACHE
    if mapping is None:
        return set_active_drum_map(None)
    return mapping
