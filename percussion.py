"""Percussion: drum map, token DSL, timelines, and plan-building.

Owns the active drum map (load/set/get), the percussion-token mini-language
(:func:`parse_single_token` / :func:`parse_pattern`), the :class:`PercHit` /
:class:`PercStage` / :class:`PercPlan` value objects, grid quantisation, the
drum-timeline builders (flat, with-fills, staged), and :func:`build_perc_from_args`
which assembles a :class:`PercPlan` from CLI args. Depends only on
:mod:`mtheory`.
"""
import json
import random
from dataclasses import dataclass, replace
from pathlib import Path

from errors import EmptyTokenError, InvalidDrumLetterError, InvalidDurationError
from mtheory import DUR_MAP, LIB_DIR

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


# Drum/percussion token payload
@dataclass(frozen=True)
class PercHit:
    note: int
    vel_offset: int = 0
    probability: float = 1.0
    flam: float | None = None
    # Micro-timing nudge in beats, delay-only (clamped to the hit's own slot
    # duration in MidiOut.drums_block) — "laid back" feel, e.g. a snare that
    # trails the grid slightly. Negative/early nudges would need to reach into
    # the previous slot, which isn't supported.
    timing_offset: float = 0.0


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

_DRUM_MAP_CACHE: dict[str, int] | None = None


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
    _DRUM_MAP_CACHE = mapping
    return mapping


def get_drum_map() -> dict[str, int]:
    if _DRUM_MAP_CACHE is None:
        set_active_drum_map(None)
    return _DRUM_MAP_CACHE


def choose_perc_pattern(main, interrupters, fill_rate):
    """
    Returns either the main percussion pattern or a fill interrupter
    depending on fill_rate probability.
    """
    if interrupters and fill_rate > 0.0 and random.random() < fill_rate:
        return random.choice(interrupters)
    return main


def parse_single_token(tok: str,
                       drum_map: dict[str, int] | None = None
                       ) -> tuple[float, list[PercHit]]:
    """
    Token grammar:
      <len><letters>  e.g., 'qksh' (quarter: kick+snare+hat)
      <len>r          rest (no hits) e.g., 'er' (eighth rest)
    Letter symbols follow the active drum map (see library/percussion_library.json).
    Modifiers per letter:
      [vel±N] adjust velocity before humanisation
      [probX] plays with probability X (0–1)
      [flamX] adds a second hit X beats later (>=0)
    Returns (beats, [PercHit,...])
    """
    tok = tok.strip()
    if not tok:
        raise EmptyTokenError("Empty percussion token")
    ln = tok[0].lower()
    if ln not in DUR_MAP:
        raise InvalidDurationError(f"Bad duration in token '{tok}'")
    beats = DUR_MAP[ln]
    if len(tok) == 1:
        raise InvalidDurationError(f"Incomplete token '{tok}' (needs instruments or 'r')")
    rest = tok[1:]
    if rest.lower() == "r":
        return (beats, [])
    drum_map = drum_map or get_drum_map()
    hits: list[PercHit] = []
    i = 0
    rest_len = len(rest)
    while i < rest_len:
        ch = rest[i]
        if ch.isspace():
            i += 1
            continue
        if ch == '[':
            raise ValueError(f"Unexpected '[' in token '{tok}'")
        key = ch.lower()
        if key not in drum_map:
            raise InvalidDrumLetterError(f"Unknown drum letter '{ch}' in token '{tok}'")
        i += 1
        vel_offset = 0
        probability = 1.0
        flam = None
        timing_offset = 0.0
        if i < rest_len and rest[i] == '[':
            end = rest.find(']', i)
            if end == -1:
                raise ValueError(f"Unclosed modifier block in token '{tok}'")
            block = rest[i + 1:end]
            i = end + 1
            if block.strip():
                for raw in block.split(','):
                    part = raw.strip()
                    if not part:
                        continue
                    lower = part.lower()
                    if lower.startswith('vel'):
                        payload = part[3:]
                        if payload.startswith(('=', '+', '-')):
                            payload = payload[1:] if payload.startswith('=') else payload
                        payload = payload.strip()
                        if not payload:
                            raise ValueError(
                                f"Missing velocity offset in modifier '{part}'")
                        try:
                            offset_val = int(payload)
                        except ValueError as exc:
                            raise ValueError(
                                f"Bad velocity offset '{part}' in token '{tok}'") from exc
                        if lower.startswith('vel-') and not lower.startswith('vel-='):
                            offset_val = -abs(offset_val)
                        elif lower.startswith('vel+') and not lower.startswith('vel+='):
                            offset_val = abs(offset_val)
                        vel_offset = offset_val
                    elif lower.startswith('prob'):
                        payload = part[4:]
                        if payload.startswith('='):
                            payload = payload[1:]
                        try:
                            probability = float(payload)
                        except ValueError as exc:
                            raise ValueError(
                                f"Bad probability '{part}' in token '{tok}'") from exc
                        probability = max(0.0, min(1.0, probability))
                    elif lower.startswith('flam'):
                        payload = part[4:]
                        if payload.startswith('='):
                            payload = payload[1:]
                        try:
                            flam_val = float(payload)
                        except ValueError as exc:
                            raise ValueError(
                                f"Bad flam offset '{part}' in token '{tok}'") from exc
                        if flam_val < 0.0:
                            raise ValueError(
                                f"Flam offset must be >=0 in token '{tok}'")
                        flam = flam_val
                    elif lower.startswith('to'):
                        payload = part[2:]
                        if payload.startswith(('=', '+', '-')):
                            payload = payload[1:] if payload.startswith('=') else payload
                        payload = payload.strip()
                        if not payload:
                            raise ValueError(
                                f"Missing timing offset in modifier '{part}'")
                        try:
                            offset_val = float(payload)
                        except ValueError as exc:
                            raise ValueError(
                                f"Bad timing offset '{part}' in token '{tok}'") from exc
                        if lower.startswith('to-') and not lower.startswith('to-='):
                            offset_val = -abs(offset_val)
                        elif lower.startswith('to+') and not lower.startswith('to+='):
                            offset_val = abs(offset_val)
                        timing_offset = offset_val
                    else:
                        raise ValueError(
                            f"Unknown modifier '{part}' in token '{tok}'")
        note_val = drum_map[key]
        hits.append(
            PercHit(note=note_val,
                    vel_offset=int(vel_offset),
                    probability=probability,
                    flam=flam,
                    timing_offset=timing_offset))
    return (beats, hits)


def _split_tokens_bracket_aware(text: str) -> list[str]:
    """Split on commas, but preserve commas inside [...] modifier blocks."""
    parts = []
    depth = 0
    cur = ""
    for ch in text or "":
        if ch == "[":
            depth += 1
            cur += ch
        elif ch == "]":
            depth -= 1
            cur += ch
        elif ch == "," and depth == 0:
            if cur.strip():
                parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def parse_pattern(text: str,
                  drum_map: dict[str, int] | None = None
                  ) -> list[tuple[float, list[PercHit]]]:
    """
    Comma-separated percussion tokens -> list of (beats, hits)
    Preserves commas inside [...] modifier blocks (e.g., [vel+10,prob0.5]).
    Example: "qk,eh,esh[vel+5,prob0.8],er,ek"
    """
    parts = _split_tokens_bracket_aware(text)
    drum_map = drum_map or get_drum_map()
    return [parse_single_token(p, drum_map) for p in parts]


def parse_many_patterns(items: list[str],
                        drum_map: dict[str, int] | None = None
                        ) -> list[list[tuple[float, list[PercHit]]]]:
    """List of pattern strings -> list of parsed patterns."""
    drum_map = drum_map or get_drum_map()
    return [parse_pattern(s, drum_map) for s in items]


GRID_STEP = 0.125  # 32nd = 0.125 beats (supports 8th/16th/32nd)


def quantize_to_grid(pattern: list[tuple[float, list[PercHit]]],
                     step: float = GRID_STEP) -> list[tuple[float, list[PercHit]]]:
    """
    Expand a pattern into fixed-step slots (e.g., 32nds), so it loops exactly.
    Input pattern: list of (beats, hits_set). Rest = empty set().
    Output: list of (step_beats, hits) slots, length is multiple of step.
    Every token is guaranteed at least 1 slot (no silent drops).
    """
    out: list[tuple[float, list[PercHit]]] = []
    for beats, hits in pattern:
        if beats <= 0:
            continue
        # Ensure every token gets at least 1 slot, even if rounds to <1.
        slots = max(1, int(round(beats / step)))
        # distribute duration across 'slots' fixed cells
        for i in range(slots):
            out.append(
                (step,
                 hits if i == 0 and hits else []))  # hit on first slot only
    return out


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


def parse_pocket_spec(spec: str,
                      drum_map: dict[str, int] | None = None) -> dict[int, float]:
    """Parse a pocket spec like ``"c:0.03,d:0.02"`` into {midi_note: beats}.

    Each entry is <drum letter>:<delay in beats>; the delay is applied by
    :func:`apply_pocket`. Raises ValueError on unknown letters or bad numbers.
    """
    drum_map = drum_map or get_drum_map()
    out: dict[int, float] = {}
    for part in (p.strip() for p in (spec or "").split(",") if p.strip()):
        if ":" not in part:
            raise ValueError(f"Pocket entry must be letter:beats, got '{part}'")
        letter, raw = (s.strip() for s in part.split(":", 1))
        if letter.lower() not in drum_map:
            raise InvalidDrumLetterError(f"Unknown drum letter '{letter}' in pocket spec")
        try:
            beats = float(raw)
        except ValueError as exc:
            raise ValueError(f"Bad pocket delay '{raw}' for '{letter}'") from exc
        if beats < 0.0:
            raise ValueError(f"Pocket delay must be >=0 for '{letter}' "
                             "(early nudges aren't supported)")
        out[drum_map[letter.lower()]] = beats
    return out


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


def parse_chord_interrupters(
        motifs: list[str]) -> list[list[tuple[float, str]]]:
    """
    Motif token grammar (chords): same lengths; 'c' means play chord, 'r' rest.
    Example: "ec,er,sc" -> [(0.5,'c'), (0.5,'r'), (0.25,'c')]
    """
    out = []
    for m in motifs:
        seq = []
        for tok in [t.strip() for t in m.split(",") if t.strip()]:
            ln = tok[0].lower()
            if ln not in DUR_MAP:
                raise ValueError(f"Bad chord interrupter token '{tok}'")
            beats = DUR_MAP[ln]
            flag = tok[1:].lower()
            if flag not in ("c", "r"):
                raise ValueError(
                    f"Chord interrupter must end with c/r: '{tok}'")
            seq.append((beats, flag))
        out.append(seq)
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
