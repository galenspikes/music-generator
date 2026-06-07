"""Curated song generator presets for the Fluidsynth toolkit.

Each recipe describes a ready-to-run `play_music` invocation for a specific
style. The executor script can look these up and bake the appropriate command
line.
"""

from __future__ import annotations

from typing import Dict, Iterable, Tuple


def _slugify(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


SONG_COOKBOOK: Dict[str, Dict[str, object]] = {
    "salsa": {
        "title": "Salsa Brava",
        "description": (
            "Bright salsa progression with brass lead, clave-driven percussion,"
            " and lively counterpoint lines."
        ),
        "args": [
            "--mode",
            "mixed",
            "--keys",
            "C,F,G,Bb",
            "--bpm",
            "188",
            "--instrument",
            "trumpet",
            "--chords",
            "extended-chords",
            "ninths",
            "--chords-order",
            "roundrobin",
            "--satb-style",
            "counterpoint",
            "--counterpoint-step",
            "0.25",
            "--counterpoint-suspension-prob",
            "0.45",
            "--counterpoint-anticipation-prob",
            "0.30",
            "--perc-lib",
            "library/percussion_library.json",
            "--perc-main-key",
            "salsa:4/4:clave-3-2",
            "--perc-fill-rate",
            "0.35",
            "--velocity-mode-drums",
            "human",
            "--seconds",
            "90",
        ],
        "aliases": ["latin", "salsa_brava"],
        "tags": ["latin", "dance", "bright"],
    },
    "rock": {
        "title": "Arena Rock Pulse",
        "description": (
            "Driving rock anthem with distorted guitar, high-energy drums,"
            " and round-robin chord movement."
        ),
        "args": [
            "--mode",
            "mixed",
            "--keys",
            "E,A,D",
            "--bpm",
            "144",
            "--instrument",
            "distguitar",
            "--chords",
            "triads",
            "sevenths",
            "--chords-order",
            "roundrobin",
            "--satb-style",
            "block",
            "--velocity-mode-drums",
            "human",
            "--perc-lib",
            "library/percussion_library.json",
            "--perc-main-key",
            "rock:4/4:fast",
            "--perc-interrupter-keys",
            "rock:4/4:halftime",
            "--perc-fill-rate",
            "0.28",
            "--seconds",
            "75",
        ],
        "aliases": ["arena", "rock_fast"],
        "tags": ["rock", "electric", "energetic"],
    },
    "rnb": {
        "title": "Midnight R&B",
        "description": (
            "Smooth R&B vibe with electric piano, extended chords,"
            " humanized dynamics, and soulful counterpoint."
        ),
        "args": [
            "--mode",
            "mixed",
            "--keys",
            "Eb,Gb,Bb",
            "--bpm",
            "92",
            "--instrument",
            "epiano",
            "--chords",
            "extended-chords",
            "ninths",
            "sus",
            "--chords-order",
            "roundrobin",
            "--satb-style",
            "counterpoint",
            "--counterpoint-step",
            "0.50",
            "--counterpoint-suspension-prob",
            "0.35",
            "--counterpoint-anticipation-prob",
            "0.40",
            "--velocity-mode-chords",
            "human",
            "--velocity-mode-drums",
            "human",
            "--perc-lib",
            "library/percussion_library.json",
            "--perc-main-key",
            "funk:4/4:med",
            "--perc-fill-rate",
            "0.22",
            "--seconds",
            "80",
        ],
        "aliases": ["soul", "r&b"],
        "tags": ["rnb", "groove", "smooth"],
    },
    "bach_prelude": {
        "title": "Prelude in C Style",
        "description": (
            "A flowing homage to Bach's Well-Tempered Clavier Prelude in C,"
            " with steady sixteenth-note motion and gentle harmonic shifts."
    ),
    "args": [
        "--mode",
        "complete",
        "--keys",
        "C::maj,"
        "D:3:min7,"
        "G:1:7,"
        "C::maj,"
        "A:1:min,"
        "D:3:7,"
        "G:1:maj,"
        "C:3:maj7,"
        "A::min7,"
        "D::7,"
        "G::maj,"
        "G::dim7,"
        "D:1:min,"
        "F::dim7,"
        "C:1:maj,"
        "F:3:maj7,"
        "D::min7,"
        "G::7,"
        "C::7,"
        "F::maj7,"
        "F#::dim7,"
        "G#::dim7,"
        "G::7,"
        "C:2:maj,"
        "G::9,"
        "G::7,"
        "G::7b9,"
        "C:2:maj,"
        "G::9,"
        "G::7,"
        "C::7,"
        "F:2:maj,"
        "G::7b9,"
        "C::maj",
        "--bpm",
        "80",
        "--instrument",
        "piano",
        "--chords",
        "triads",
        "sevenths",
        "add6",
        "--chords-order",
        "roundrobin",
        "--chord-length",
        "w",
        "--satb-style",
        "arpeggio",
        "--counterpoint-step",
        "0.25",
        "--velocity-mode-chords",
        "human",
        "--perc-main",
        "qr,qr,qr,qr",
        "--perc-fill-rate",
        "0.0",
        "--seconds",
        "150",
    ],
        "aliases": ["bach", "prelude", "baroque"],
        "tags": ["classical", "baroque", "counterpoint"],
    },
    "bach_counterpoint": {
        "title": "Prelude Counterpoint Study",
        "description": (
            "A contrapuntal exploration of the Prelude in C harmony,"
            " voiced with independent SATB motion and subtle suspensions."
        ),
        "args": [
            "--mode",
            "complete",
            "--keys",
            "C::maj,"
            "D:3:min7,"
            "G:1:7,"
            "C::maj,"
            "A:1:min,"
            "D:3:7,"
            "G:1:maj,"
            "C:3:maj7,"
            "A::min7,"
            "D::7,"
            "G::maj,"
            "G::dim7,"
            "D:1:min,"
            "F::dim7,"
            "C:1:maj,"
            "F:3:maj7,"
            "D::min7,"
            "G::7,"
            "C::7,"
            "F::maj7,"
            "F#::dim7,"
            "G#::dim7,"
            "G::7,"
            "C:2:maj,"
            "G::9,"
            "G::7,"
            "G::7b9,"
            "C:2:maj,"
            "G::9,"
            "G::7,"
            "C::7,"
            "F:2:maj,"
            "G::7b9,"
            "C::maj",
            "--bpm",
            "80",
            "--instrument",
            "saw",
            "--chords",
            "triads",
            "sevenths",
            "add6",
            "--chords-order",
            "roundrobin",
            "--chord-length",
            "w",
        "--satb-style",
        "counterpoint",
        "--counterpoint-step",
        "0.08",
        "--counterpoint-suspension-prob",
        "0.10",
        "--counterpoint-anticipation-prob",
        "0.25",
            "--velocity-mode-chords",
            "human",
            "--perc-main",
            "qr,qr,qr,qr",
            "--perc-fill-rate",
            "0.0",
            "--seconds",
            "150",
        ],
        "aliases": ["bach_counter", "prelude_counterpoint"],
        "tags": ["classical", "baroque", "counterpoint"],
    },
}


def recipe_keys() -> Iterable[str]:
    return SONG_COOKBOOK.keys()


def resolve_recipe(name: str) -> Tuple[str, Dict[str, object]]:
    slug = _slugify(name)
    if slug in SONG_COOKBOOK:
        return slug, SONG_COOKBOOK[slug]
    for key, payload in SONG_COOKBOOK.items():
        for alias in payload.get("aliases", []):
            if _slugify(alias) == slug:
                return key, payload
    raise KeyError(f"Unknown recipe '{name}'.")


def format_command(args: Iterable[str]) -> str:
    import shlex

    return " ".join(shlex.quote(part) for part in args)
