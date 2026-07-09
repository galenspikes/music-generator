# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""The percussion-token mini-language: parsing text patterns into hits.

Owns :class:`PercHit`, :func:`parse_single_token` / :func:`parse_pattern` /
:func:`parse_many_patterns`, grid quantisation, the chord-interrupter motif
grammar, and pocket-spec parsing. Depends on :mod:`percussion_map` (for the
default drum map) and :mod:`mtheory`. Part of the :mod:`percussion` package
of modules — import through :mod:`percussion` unless you specifically want
this layer. Grammar reference: ``docs/reference/token-grammar.md``.
"""
from dataclasses import dataclass

from errors import EmptyTokenError, InvalidDrumLetterError, InvalidDurationError
from mtheory import DUR_MAP
from percussion_map import get_drum_map

__all__ = [
    "PercHit",
    "parse_single_token",
    "parse_pattern",
    "parse_many_patterns",
    "GRID_STEP",
    "quantize_to_grid",
    "parse_chord_interrupters",
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


def parse_pocket_spec(spec: str,
                      drum_map: dict[str, int] | None = None) -> dict[int, float]:
    """Parse a pocket spec like ``"c:0.03,d:0.02"`` into {midi_note: beats}.

    Each entry is <drum letter>:<delay in beats>; the delay is applied by
    :func:`percussion_timeline.apply_pocket`. Raises ValueError on unknown
    letters or bad numbers.
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
