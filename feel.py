# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""Genre feel presets: named bundles of the groove knobs (Thread 3 v3).

A *feel* expands to a section-config fragment — swing amount, ghost-note
rate, a snare pocket (per-drum delay), kick-locked bass — so one word buys a
coherent groove instead of hand-tuning four knobs. Precedence in the
arrangement layer: engine defaults < feel < the user's explicit values, so
naming a feel never overrides something the song author wrote out.

The raw knobs all shipped first (`swing`, `perc.ghost_rate`, `perc.pocket`,
`bass.lock_kick`); a preset is nothing but values for them, so anything a
preset does can be reproduced or overridden knob-by-knob. Delay values are
in beats (0.02 beats ~ 10 ms at 120 bpm — pocket, not sloppiness).

Leaf module: no internal imports, usable from any layer.
"""

from __future__ import annotations

import copy

__all__ = ["FEEL_PRESETS", "expand_feel", "list_feels"]

FEEL_PRESETS: dict[str, dict] = {
    # Everything on the grid, no ornamentation — machine pop / techno.
    "tight": {
        "swing": 0.0,
        "perc": {"ghost_rate": 0.0, "pocket": {}},
    },
    # A relaxed backbeat: snare sits behind the grid, light ghosts.
    "laidback": {
        "swing": 0.10,
        "perc": {"ghost_rate": 0.10, "pocket": {"c": 0.035, "d": 0.035}},
    },
    # Triplet swing with a slightly settled snare — jazz / shuffle.
    "swing": {
        "swing": 0.5,
        "perc": {"ghost_rate": 0.08, "pocket": {"c": 0.02, "d": 0.02}},
    },
    # Syncopated and busy: heavy ghosts, a hint of swing, bass on the kick.
    "funk": {
        "swing": 0.15,
        "perc": {"ghost_rate": 0.22, "pocket": {"c": 0.015, "d": 0.015}},
        "bass": {"lock_kick": True},
    },
}


def list_feels() -> list[str]:
    return sorted(FEEL_PRESETS)


def expand_feel(name: str) -> dict:
    """Return the section-config fragment for a feel (a deep copy — callers
    merge it, and merging must never mutate the preset table)."""
    key = str(name).strip().lower()
    if key not in FEEL_PRESETS:
        raise ValueError(
            f"Unknown feel '{name}'. Choices: {', '.join(list_feels())}")
    return copy.deepcopy(FEEL_PRESETS[key])
