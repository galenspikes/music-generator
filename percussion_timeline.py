# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""Drum timelines: unrolling parsed percussion patterns over a piece.

Owns :class:`PercStage` / :class:`PercPlan`, the timeline builders (flat,
with-fills, staged), the timeline transforms (pocket, ghost notes, kick
onsets), and :func:`build_perc_from_args` which assembles a
:class:`PercPlan` from CLI args. Depends on :mod:`percussion_tokens` /
:mod:`percussion_map` and :mod:`mtheory`. Part of the :mod:`percussion`
package of modules — import through :mod:`percussion` unless you
specifically want this layer.
"""
import json
import random
from dataclasses import dataclass, replace

from mtheory import LIB_DIR
from percussion_map import get_drum_map
from percussion_tokens import PercHit, parse_pattern, quantize_to_grid

__all__ = [
    "PercStage",
    "PercPlan",
    "choose_perc_pattern",
    "build_drum_timeline_from_main",
    "build_drum_timeline_with_fills",
    "build_drum_segment",
    "build_drum_timeline_stages",
    "build_perc_from_args",
    "KICK_NOTES",
    "kick_onsets",
    "add_ghost_notes",
    "apply_pocket",
]


@dataclass(frozen=True)
class PercStage:
    beats: float
    main: list[tuple[float, list[PercHit]]]
    fills: tuple[list[tuple[float, list[PercHit]]], ...] | None = None


@dataclass
class PercPlan:
    main: list[tuple[float, list[PercHit]]]
    interrupters: list[list[tuple[float, list[PercHit]]]] | None
    stages: list[PercStage] | None
    fill_curve: tuple[float, float] | None


def choose_perc_pattern(main, interrupters, fill_rate):
    """
    Returns either the main percussion pattern or a fill interrupter
    depending on fill_rate probability.
    """
    if interrupters and fill_rate > 0.0 and random.random() < fill_rate:
        return random.choice(interrupters)
    return main


def build_drum_timeline_from_main(
        main_pat: list[tuple[float, list[PercHit]]],
        beats_total: float
        ) -> list[tuple[float, float, list[PercHit]]]:
    """
    Repeat 'main_pat' verbatim on a fixed grid until 'beats_total' is reached.
    Assumes 'main_pat' already quantized (e.g., via quantize_to_grid).
    Returns list of (when_beats, duration_beats, hits_set).
    """
    return build_drum_segment(0.0, beats_total, main_pat, None, 0.0)


def build_drum_timeline_with_fills(
        main_pat: list[tuple[float, list[PercHit]]],
        intr_pats: list[list[tuple[float, list[PercHit]]]] | None,
        beats_total: float,
        fill_rate: float) -> list[tuple[float, float, list[PercHit]]]:
    """
    Bar-less unroll: each iteration chooses either main or a fill motif
    based on fill_rate. If intr_pats is None or fill_rate==0, falls back to main only.
    """
    return build_drum_segment(0.0, beats_total, main_pat, intr_pats, fill_rate)


def build_drum_segment(start_beats: float,
                       duration: float,
                       main_pat: list[tuple[float, list[PercHit]]],
                       intr_pats: list[list[tuple[float, list[PercHit]]]] | None,
                       fill_rate: float) -> list[tuple[float, float, list[PercHit]]]:
    """Unroll a single percussion segment starting at start_beats."""
    if not main_pat or duration <= 0.0:
        return []
    out: list[tuple[float, float, list[PercHit]]] = []
    local = 0.0
    while local < duration:
        pattern = choose_perc_pattern(main_pat, intr_pats, fill_rate)
        for beats, hits in pattern:
            if local >= duration:
                break
            dur = min(beats, max(0.0, duration - local))
            if dur <= 0.0:
                break
            out.append((start_beats + local, dur, hits))
            local += dur
    return out


def build_drum_timeline_stages(
        stages: list[PercStage],
        beats_total: float,
        fallback_main: list[tuple[float, list[PercHit]]],
        fallback_intr: list[list[tuple[float, list[PercHit]]]] | None,
        base_fill_rate: float,
        fill_curve: tuple[float, float] | None) -> list[tuple[float, float, list[PercHit]]]:
    """Build a drum timeline from a sequence of :class:`PercStage` sections.

    Each stage plays its own main pattern (falling back to ``fallback_main``
    if it has none) and its own fills (falling back to ``fallback_intr``)
    for ``stage.beats`` beats. Stages cycle until ``beats_total`` is filled;
    a stage extending past the end is truncated. The per-stage fill rate is
    the stage's own value when set, else ``base_fill_rate`` — unless
    ``fill_curve=(start, end)`` is given, which ramps the rate linearly
    across the declared stage span instead.

    Returns ``[(when_beats, dur_beats, hits), …]`` ready for
    ``MidiOut.drums_block``.
    """
    if beats_total <= 0.0 or not stages:
        return []

    out: list[tuple[float, float, list[PercHit]]] = []
    total_stage_beats = sum(stage.beats for stage in stages)
    pos = 0.0

    for stage in stages:
        if pos >= beats_total:
            break
        segment_len = min(stage.beats, max(0.0, beats_total - pos))
        if segment_len <= 0.0:
            pos += stage.beats
            continue
        if fill_curve and total_stage_beats > 0:
            start_val, end_val = fill_curve
            frac = max(0.0, min(1.0, pos / total_stage_beats))
            stage_fill = start_val + (end_val - start_val) * frac
        else:
            stage_fill = base_fill_rate
        stage_fill = max(0.0, min(1.0, stage_fill))
        stage_fills = list(stage.fills) if stage.fills else fallback_intr
        out.extend(
            build_drum_segment(pos, segment_len, stage.main, stage_fills,
                               stage_fill))
        pos += stage.beats

    if pos < beats_total and fallback_main:
        remainder = beats_total - pos
        out.extend(
            build_drum_segment(pos, remainder, fallback_main, fallback_intr,
                               base_fill_rate))

    return out


# Acoustic Bass Drum / Bass Drum 1 — the default drum map's "a"/"b" (see
# FALLBACK_DRUM_MAP). The anchor notes for a bass line "locked to the kick".
KICK_NOTES = (35, 36)


def kick_onsets(drum_tl: list[tuple[float, float, list[PercHit]]],
                kick_notes: tuple[int, ...] = KICK_NOTES) -> list[float]:
    """Onset times (beats) of kick-drum hits in a drum timeline.

    The anchor points for a bass line "locked to the kick" — see
    :func:`voicing.build_bass_line`'s ``kick_times``.
    """
    return [when for when, _dur, hits in drum_tl
            if any(h.note in kick_notes for h in hits)]


def apply_pocket(drum_tl: list[tuple[float, float, list[PercHit]]],
                 offsets: dict[int, float]
                 ) -> list[tuple[float, float, list[PercHit]]]:
    """Lay selected drums back in the pocket: set ``timing_offset`` on every
    hit whose note is in ``offsets`` ({midi_note: delay_beats}) — e.g. delay
    all snares by 0.03 beats without editing the pattern's tokens. Hits that
    already carry an explicit ``[to..]`` offset keep it (the authored token
    wins over the blanket transform). A no-op for empty ``offsets``.
    """
    if not offsets or not drum_tl:
        return drum_tl
    out: list[tuple[float, float, list[PercHit]]] = []
    for when, dur, hits in drum_tl:
        new_hits = [
            replace(h, timing_offset=offsets[h.note])
            if h.note in offsets and h.timing_offset == 0.0 else h
            for h in hits
        ]
        out.append((when, dur, new_hits))
    return out


def add_ghost_notes(
        drum_tl: list[tuple[float, float, list[PercHit]]],
        rate: float = 0.0,
        note: int = 38,
        vel_offset: int = -40
        ) -> list[tuple[float, float, list[PercHit]]]:
    """Fill empty (rest) slots in a drum timeline with a low-velocity ghost
    hit, independently at probability ``rate`` per empty slot. Slots that
    already have a hit are left untouched. A no-op at ``rate<=0``.
    """
    if rate <= 0.0 or not drum_tl:
        return drum_tl
    out = []
    for when, dur, hits in drum_tl:
        if not hits and random.random() < rate:
            out.append((when, dur, [PercHit(note=note, vel_offset=vel_offset)]))
        else:
            out.append((when, dur, hits))
    return out


def build_perc_from_args(args) -> PercPlan:
    """Build percussion plan (main loop, fills, staged evolution) from CLI args."""

    drum_map = get_drum_map()

    # Default perc_lib to the bundled library so groove lookups (perc_main_key,
    # perc_intr_keys) work out of the box on the CLI.
    if not getattr(args, "perc_lib", None):
        lib_path = LIB_DIR / "percussion_library.json"
        if lib_path.exists():
            args.perc_lib = str(lib_path)

    def parse_main(text: str) -> list[tuple[float, list[PercHit]]]:
        return quantize_to_grid(parse_pattern(text, drum_map))

    def parse_intr_list(items: list[str]) -> list[list[tuple[float, list[PercHit]]]]:
        return [quantize_to_grid(parse_pattern(item, drum_map)) for item in items]

    plan_main: list[tuple[float, list[PercHit]]] | None = None
    plan_intr: list[list[tuple[float, list[PercHit]]]] | None = None
    stage_specs: list[PercStage] = []
    fill_curve: tuple[float, float] | None = None

    perc_main_arg = getattr(args, "perc_main", None)
    if getattr(args, "no_perc", False) or perc_main_arg == "":
        plan_main = []  # explicit silence; never fall back to the default groove
    elif perc_main_arg:
        plan_main = parse_main(perc_main_arg)

    perc_intr_arg = getattr(args, "perc_interrupters", None)
    if perc_intr_arg is not None:
        # Explicitly provided (even an empty list from a bare flag) — honor it
        # instead of falling back to the default fill vocabulary below.
        plan_intr = parse_intr_list(perc_intr_arg) if perc_intr_arg else []

    groups: dict[str, dict] = {}
    if getattr(args, "perc_lib", None):
        with open(args.perc_lib, "r", encoding="utf-8") as f:
            data = json.load(f)
        groups = data.get("groups", {})

    def fetch_group(key: str) -> tuple[list[tuple[float, list[PercHit]]] | None,
                                        list[list[tuple[float, list[PercHit]]]] | None]:
        grp = groups.get(key)
        if not grp:
            return (None, None)
        mains = grp.get("main", [])
        intrs = grp.get("interrupters", [])
        main_seq = parse_main(mains[0]) if mains else None
        intr_seq = parse_intr_list(intrs) if intrs else None
        return (main_seq, intr_seq)

    if getattr(args, "perc_main_key", None):
        main_from_group, intr_from_group = fetch_group(args.perc_main_key)
        if main_from_group is not None:
            plan_main = main_from_group
        if intr_from_group:
            plan_intr = (plan_intr or []) + intr_from_group

    if getattr(args, "perc_intr_keys", None):
        for key in args.perc_intr_keys:
            _, intr_from_group = fetch_group(key)
            if intr_from_group:
                plan_intr = (plan_intr or []) + intr_from_group

    stage_tokens = getattr(args, "perc_stages", None) or []

    def parse_stage_descriptor(token: str) -> PercStage:
        if ':' not in token:
            raise ValueError(f"Percussion stage must be 'beats:pattern': '{token}'")
        beats_part, payload = token.split(":", 1)
        try:
            beats_val = float(beats_part.strip())
        except ValueError as exc:
            raise ValueError(f"Bad perc stage length in '{token}'") from exc
        if beats_val <= 0.0:
            raise ValueError(f"Percussion stage beats must be >0 in '{token}'")
        pieces = [p.strip() for p in payload.split("|") if p.strip()]
        if not pieces:
            raise ValueError(f"Percussion stage '{token}' missing pattern payload")

        stage_main: list[tuple[float, list[PercHit]]] | None = None
        stage_fills: list[list[tuple[float, list[PercHit]]]] = []

        for piece in pieces:
            if piece.startswith('@'):
                if not groups:
                    raise ValueError(
                        f"Percussion stage '{token}' references @{piece[1:]} without --perc-lib")
                g_main, g_intr = fetch_group(piece[1:])
                if g_main is not None and stage_main is None:
                    stage_main = g_main
                if g_intr:
                    stage_fills.extend(g_intr)
                continue
            if stage_main is None:
                stage_main = parse_main(piece)
            else:
                stage_fills.extend(parse_intr_list([piece]))

        if stage_main is None:
            raise ValueError(f"Percussion stage '{token}' did not resolve a main pattern")

        fills_tuple = tuple(stage_fills) if stage_fills else None
        return PercStage(beats=beats_val, main=stage_main, fills=fills_tuple)

    for token in stage_tokens:
        stage_specs.append(parse_stage_descriptor(token))

    def parse_fill_curve(raw: str) -> tuple[float, float]:
        parts = [p.strip() for p in raw.split(":") if p.strip()]
        if len(parts) != 2:
            raise ValueError("--perc-fill-curve must be 'start:end' within [0,1]")
        try:
            start_val = float(parts[0])
            end_val = float(parts[1])
        except ValueError as exc:
            raise ValueError("--perc-fill-curve expects numeric values") from exc
        for val in (start_val, end_val):
            if not 0.0 <= val <= 1.0:
                raise ValueError("perc fill curve values must be within [0,1]")
        return (start_val, end_val)

    if getattr(args, "perc_fill_curve", None):
        fill_curve = parse_fill_curve(args.perc_fill_curve)

    if plan_main is None:
        plan_main = parse_main("sh,sh,sh,sh")

    if plan_intr is None:
        plan_intr = parse_intr_list(["qk,er,qs,er"])

    return PercPlan(
        main=plan_main,
        interrupters=plan_intr,
        stages=stage_specs or None,
        fill_curve=fill_curve,
    )
