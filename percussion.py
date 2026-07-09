"""Percussion: drum map, token DSL, timelines, and plan-building.

The public façade over the three percussion layers, split for single
responsibility (each is independently testable):

- :mod:`percussion_map` — the active drum map (load/set/get);
- :mod:`percussion_tokens` — the token mini-language (:func:`parse_single_token`
  / :func:`parse_pattern`), :class:`PercHit`, grid quantisation, pocket specs;
- :mod:`percussion_timeline` — :class:`PercStage` / :class:`PercPlan`, the
  drum-timeline builders (flat, with-fills, staged), timeline transforms, and
  :func:`build_perc_from_args`.

Every historical ``percussion.X`` name is re-exported here, so this module
remains the import point for callers (and for ``music_generator``'s star
re-export). Depends only on :mod:`mtheory` (via the layers above).
"""
from percussion_map import (  # noqa: F401
    DEFAULT_PERC_LIB,
    FALLBACK_DRUM_MAP,
    get_drum_map,
    load_drum_map_from,
    set_active_drum_map,
)
from percussion_tokens import (  # noqa: F401
    GRID_STEP,
    PercHit,
    parse_chord_interrupters,
    parse_many_patterns,
    parse_pattern,
    parse_pocket_spec,
    parse_single_token,
    quantize_to_grid,
)
from percussion_timeline import (  # noqa: F401
    KICK_NOTES,
    PercPlan,
    PercStage,
    add_ghost_notes,
    apply_pocket,
    build_drum_segment,
    build_drum_timeline_from_main,
    build_drum_timeline_stages,
    build_drum_timeline_with_fills,
    build_perc_from_args,
    choose_perc_pattern,
    kick_onsets,
)

__all__ = [
    "PercHit",
    "PercStage",
    "PercPlan",
    "DEFAULT_PERC_LIB",
    "FALLBACK_DRUM_MAP",
    "load_drum_map_from",
    "set_active_drum_map",
    "get_drum_map",
    "choose_perc_pattern",
    "parse_single_token",
    "parse_pattern",
    "parse_many_patterns",
    "GRID_STEP",
    "quantize_to_grid",
    "build_drum_timeline_from_main",
    "build_drum_timeline_with_fills",
    "build_drum_segment",
    "build_drum_timeline_stages",
    "parse_chord_interrupters",
    "build_perc_from_args",
    "KICK_NOTES",
    "kick_onsets",
    "add_ghost_notes",
    "apply_pocket",
    "parse_pocket_spec",
]
