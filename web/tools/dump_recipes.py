"""Emit web/recipes.json: the engine's chord recipes, grouped for the builder UI.

Single source of truth is library/chord_recipes.py (via the engine loader); this
keeps the visual builder's Quality dropdown in lock-step with what the engine can
actually render. Run from web/:  python tools/dump_recipes.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
import music_generator as mg  # noqa: E402

# Friendly grouping; any recipe not listed lands in "More".
GROUPS = [
    ("Triads", ["maj", "min", "dim", "aug", "5", "5add8", "5add9"]),
    ("Sixths & Sevenths", ["maj7", "min7", "7", "m7b5", "hdim7", "dim7", "mmaj7",
                            "7b5", "7#5", "majadd6", "minadd6"]),
    ("Ninths, 11ths & 13ths", ["9", "maj9", "min9", "11", "min11", "13", "min13",
                               "maj7add9", "min7add9", "majadd9", "minadd9",
                               "majadd11", "minadd11", "majadd13", "majaddb13",
                               "majadd#9", "majadd#11", "majaddb9", "add4",
                               "maj7#11", "min7#11", "maj7split3", "split3", "7split3"]),
    ("Altered Dominants", ["7b9", "7#9", "7b13", "7#13", "7#11", "7b11", "7alt", "lyd-dom"]),
    ("Suspended", ["sus2", "sus4", "sus2add6", "sus2add7", "sus4add7"]),
    ("Quartal & Quintal", ["quartal", "quartal7", "quintal", "so_what", "lydian_stack"]),
    ("Clusters", ["chromatic_cluster", "diatonic_cluster", "tone_cluster_3",
                  "tone_cluster_4", "tone_cluster_5"]),
    ("Aug-6th & Chromatic", ["it6", "fr6", "ger6", "n6", "tristan"]),
    ("Spectral & Exotic", ["mystic", "petrushka", "whole_tone", "wholetone_tet",
                           "octatonic_tet", "messiaen_dom", "messiaen_resonance",
                           "messiaen_resonance_pc", "augurs", "bartok"]),
]


def main() -> None:
    available = set(mg.load_chord_recipes().keys())
    out = []
    placed = set()
    for label, names in GROUPS:
        present = [n for n in names if n in available]
        placed.update(present)
        if present:
            out.append({"label": label, "recipes": present})
    leftover = sorted(available - placed)
    if leftover:
        out.append({"label": "More", "recipes": leftover})
    dest = Path(__file__).resolve().parent.parent / "recipes.json"
    dest.write_text(json.dumps(out, indent=1))
    total = sum(len(g["recipes"]) for g in out)
    print(f"Wrote {dest} — {total} recipes in {len(out)} groups "
          f"({len(available)} available in engine)")


if __name__ == "__main__":
    main()
