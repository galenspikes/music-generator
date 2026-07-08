# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""Lead/hook generator: a monophonic, motif-based melody over the changes.

The lead is the part a listener hums — distinct from the SATB soprano (which
voices harmony) and from a section's authored ``melody`` (a literal tune).
Here a short *motif* is stated and then developed across the section:

- **Motif**: user-authored in the scale-degree grammar (``q1 e2 e3 q5``, see
  :mod:`melody`), or generated from a rhythm-cell pool + a stepwise contour
  walk (``density`` picks the pool, busier or sparser).
- **Phrase plan**: one phrase per bar, cycling call-and-response —
  statement, response (or silence, per ``rests``), restatement fitted to the
  current chord, development (inversion / sequence) — with a cadence snap at
  the end of the section.
- **Realization** (the hybrid pitch rule): degrees resolve against the
  section key/mode scale; notes falling on strong beats are snapped to the
  nearest tone of the chord sounding underneath them, so the line always
  agrees with the harmony while weak beats keep scale-step motion.

Randomness comes from the module-level :mod:`random` stream, so ``--seed``
makes the lead reproducible. Depends on :mod:`mtheory` and :mod:`melody`.
"""

from __future__ import annotations

import math
import random

import melody as mel
from melody import MelodyNote
from mtheory import ChordDef, clamp_to_range

__all__ = ["LEAD_REGISTERS", "PHRASE_BEATS", "build_lead_events",
           "generate_motif"]

# Playable window per register choice (MIDI note bounds for the lead line).
LEAD_REGISTERS: dict[str, tuple[int, int]] = {
    "low": (48, 72),   # C3–C5
    "mid": (55, 79),   # G3–G5
    "high": (62, 86),  # D4–D6
}

PHRASE_BEATS = 4.0  # one 4/4 bar per phrase slot

# Rhythm cells per density tier: durations in beats, None = rest. Each cell
# sums to PHRASE_BEATS with silence built in — the space is part of the hook.
_RHYTHM_CELLS: dict[str, list[list[float | None]]] = {
    "sparse": [
        [1.0, None, 1.0, 1.0, None],            # rests: 0.5-beat placeholders
        [1.5, 0.5, None, 1.0, None],
        [2.0, 1.0, None, None],
    ],
    "medium": [
        [0.5, 0.5, 1.0, None, 0.5, 0.5, None],
        [1.0, 0.5, 0.5, 1.0, None, None],
        [0.5, 0.5, 0.5, 0.5, 1.0, None, None],
    ],
    "busy": [
        [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, None, None],
        [0.25, 0.25, 0.5, 0.5, 0.5, 1.0, None, None],
        [0.5, 0.25, 0.25, 0.5, 0.5, 0.5, 0.5, None, None],
    ],
}
_REST_SLOT = 0.5  # each None above stands for this much silence


def _density_tier(density: float) -> str:
    if density < 0.35:
        return "sparse"
    if density < 0.7:
        return "medium"
    return "busy"


def generate_motif(density: float = 0.5) -> list[MelodyNote]:
    """Invent a one-bar motif: a rhythm cell from the density tier plus a
    stepwise contour walk over scale degrees (leaps resolve by step back).
    Ends on a stable degree (1/3/5) so restatements feel grounded."""
    cell = random.choice(_RHYTHM_CELLS[_density_tier(density)])
    degrees: list[int] = []
    cur = random.choice((1, 3, 5))
    pending_resolve = 0
    n_notes = sum(1 for d in cell if d is not None)
    for i in range(n_notes):
        degrees.append(cur)
        if i == n_notes - 2:
            # aim the last note at the nearest stable degree (any octave, so
            # a walk that has climbed doesn't plunge back to the base octave)
            stable = [s + 7 * k for s in (1, 3, 5) for k in (-1, 0, 1)]
            cur = min(stable, key=lambda s: abs(s - cur))
            continue
        if pending_resolve:
            cur += -1 if pending_resolve > 0 else 1  # step back after a leap
            pending_resolve = 0
        else:
            step = random.choices((-1, 1, -2, 2, 4), weights=(30, 34, 12, 14, 10))[0]
            if abs(step) > 2:
                pending_resolve = step
            cur += step
    out: list[MelodyNote] = []
    it = iter(degrees)
    for dur in cell:
        if dur is None:
            out.append(MelodyNote(None, 0, 0, _REST_SLOT, True))
        else:
            deg = next(it)
            octave, idx = divmod(deg - 1, 7)
            out.append(MelodyNote(idx + 1, 0, octave, dur, False))
    return out


def _motif_beats(notes: list[MelodyNote]) -> float:
    return sum(n.beats for n in notes)


def _span_at(spans: list[tuple[float, float, ChordDef]],
             when: float) -> ChordDef | None:
    for start, end, chord in spans:
        if start <= when < end:
            return chord
    return spans[-1][2] if spans else None


def _nearest_chord_tone(target: int, chord: ChordDef, lo: int, hi: int) -> int:
    cands = [n for n in range(lo, hi + 1) if n % 12 in chord.pcs]
    if not cands:
        return clamp_to_range(target, lo, hi)
    return min(cands, key=lambda n: abs(n - target))


def _realize_phrase(notes: list[MelodyNote],
                    phrase_start: float,
                    spans: list[tuple[float, float, ChordDef]],
                    key_pc: int,
                    scale: list[int],
                    lo: int,
                    hi: int,
                    shift: int | None
                    ) -> tuple[list[tuple[float, float, int]], int | None]:
    """Realize one phrase's notes onto the global beat frame.

    Hybrid pitch rule: each degree resolves against the section scale on a
    fixed octave line, transposed once into the register (``shift``, chosen
    at the section's first note and kept for the rest) so every melodic
    interval sounds exactly as written — including leaps — with per-note
    octave folding only when the line drifts past the register edge. Onsets
    on strong beats (1 and 3 of the bar) snap to the nearest tone of the
    chord underneath. Returns (events, shift).
    """
    out: list[tuple[float, float, int]] = []
    when = phrase_start
    center = (lo + hi) // 2
    for note in notes:
        if note.is_rest or note.degree is None:
            when += note.beats
            continue
        val = (key_pc + scale[(note.degree - 1) % 7] + note.accidental
               + 12 * note.octave)
        if shift is None:
            shift = 12 * round((center - val) / 12)
        pitch = val + shift
        while pitch < lo:
            pitch += 12
        while pitch > hi:
            pitch -= 12
        if (when % 2.0) < 1e-6:  # strong beat: agree with the harmony
            chord = _span_at(spans, when)
            if chord is not None:
                pitch = _nearest_chord_tone(pitch, chord, lo, hi)
        out.append((when, note.beats, pitch))
        when += note.beats
    return out, shift


def _develop(motif: list[MelodyNote],
             chord: ChordDef | None,
             key_pc: int,
             scale: list[int],
             device: str) -> list[MelodyNote]:
    """Apply a development device to the motif (v2: the hook grows)."""
    if device == "fit" and chord is not None:
        shift = mel._root_degree_in_scale(chord.root_pc, key_pc, scale)
        return mel.transpose_diatonic(motif, shift)
    if device == "invert":
        axis = next((n.degree for n in motif if not n.is_rest), 1)
        return mel.invert(motif, axis_degree=axis)
    if device == "sequence":
        return mel.transpose_diatonic(motif, -1)
    return motif


def build_lead_events(spans: list[tuple[float, float, ChordDef]],
                      key_pc: int,
                      mode: str,
                      *,
                      motif_text: str | None = None,
                      density: float = 0.5,
                      rests: float = 0.3,
                      register: str = "high"
                      ) -> list[tuple[float, float, int]]:
    """Build the lead line for one section.

    ``spans`` = [(start_beats, end_beats, ChordDef)] covering the section from
    beat 0; the returned ``[(when, dur, midi_note)]`` events are in the same
    (section-relative) beat frame. ``motif_text`` (scale-degree grammar) is
    developed as-is when given, else a motif is generated per ``density``.
    ``rests`` is the probability that a response phrase stays silent
    (call-and-response space). ``register`` picks the playable window.
    """
    if not spans:
        return []
    total = spans[-1][1]
    lo, hi = LEAD_REGISTERS.get(str(register).lower(), LEAD_REGISTERS["high"])
    scale = mel.scale_for(mode)
    rests = max(0.0, min(1.0, float(rests)))

    if motif_text and str(motif_text).strip():
        motif = mel.parse_melody(str(motif_text))
    else:
        motif = generate_motif(density)
    phrase_len = max(PHRASE_BEATS, math.ceil(_motif_beats(motif)))

    events: list[tuple[float, float, int]] = []
    shift: int | None = None
    phrase_idx = 0
    pos = 0.0
    while pos < total - 1e-6:
        slot = phrase_idx % 4
        chord = _span_at(spans, pos)
        if slot == 0:
            notes = motif                      # statement
        elif slot == 1:
            if random.random() < rests:
                notes = None                   # response space: silence
            else:
                notes = _develop(motif, chord, key_pc, scale, "fit")
        elif slot == 2:
            notes = _develop(motif, chord, key_pc, scale, "fit")
        else:
            device = random.choice(("invert", "sequence"))
            notes = _develop(motif, chord, key_pc, scale, device)
        if notes is not None:
            phrase_events, shift = _realize_phrase(
                notes, pos, spans, key_pc, scale, lo, hi, shift)
            events.extend(phrase_events)
        phrase_idx += 1
        pos += phrase_len

    # truncate at the section boundary, then cadence: land the final note on
    # a tone of the chord it sounds over, whatever beat it falls on
    events = [(w, min(d, total - w), n) for (w, d, n) in events
              if w < total - 1e-6]
    if events:
        w, d, n = events[-1]
        chord = _span_at(spans, w)
        if chord is not None:
            events[-1] = (w, d, _nearest_chord_tone(n, chord, lo, hi))
    return events
