# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""Fugue generator (v1: exposition + cadence).

Builds a fugal **exposition** on the four SATB voice-channels:
- voices enter one at a time with the subject (tonic) / answer (dominant),
- the just-finished voice continues with the countersubject,
- older voices fill in consonant free lines drawn from the block's harmony,
- a short cadence closes it.

This is an *exposition*, not a complete fugue — episodes, middle entries in
related keys, and stretto/inversion/augmentation devices are v2/v3. It stands on
the melody primitive: the answer is `transpose_diatonic(subject, +4)`, the
default countersubject is `invert(subject)`, etc.

See docs/design-notes/melody-primitive-plan.md and docs/design-notes/arrangement-plan.md.
"""

from __future__ import annotations

import melody as mel
import music_generator as mg

# Entry plan: (voice, material) where material alternates Subject/Answer
# (tonic/dominant). Registers spread mid -> up -> top -> bottom.
ENTRY_PLAN = [
    ("tenor", "S"),
    ("alto", "A"),
    ("soprano", "S"),
    ("bass", "A"),
]

VOICE_RANGES = {
    "soprano": mg.SOP_RANGE,
    "alto": mg.ALTO_RANGE,
    "tenor": mg.TENOR_RANGE,
    "bass": mg.BASS_RANGE,
}


def _free_line(block: int, slot: int, span: float) -> list[mel.MelodyNote]:
    """A consonant filler line for an older voice over one block.

    Even blocks are tonic, odd blocks dominant; each voice (`slot`) takes a
    different chord tone so simultaneous free voices don't move in parallel.
    """
    triad = [1, 3, 5] if block % 2 == 0 else [5, 7, 2]  # I or V
    a = triad[slot % 3]
    b = triad[(slot + 1) % 3]
    half = span / 2.0
    return [
        mel.MelodyNote(a, 0, 0, half, False),
        mel.MelodyNote(b, 0, 0, half, False),
    ]


def _cadence(span: float) -> dict[str, list[mel.MelodyNote]]:
    """A V -> I authentic cadence: each voice gets a V tone then a held I tone."""
    half = max(0.5, span / 2.0)
    whole = span
    # (V degree, I degree) per voice
    plan = {
        "soprano": (2, 1),   # 9/2 -> tonic
        "alto": (7, 3),      # leading tone -> 3rd
        "tenor": (5, 5),     # dominant -> 5th
        "bass": (5, 1),      # dominant -> tonic
    }
    out = {}
    for voice, (v_deg, i_deg) in plan.items():
        out[voice] = [
            mel.MelodyNote(v_deg, 0, 0, half, False),
            mel.MelodyNote(i_deg, 0, 0, whole, False),
        ]
    return out


def build_fugue(subject: str,
                key_pc: int,
                mode: str,
                countersubject: str | None = None
                ) -> tuple[list[tuple[str, float, float, int]], float]:
    """Build a fugal exposition + cadence.

    Returns ``(events, total_beats)`` where each event is
    ``(voice_name, when_beats, dur_beats, midi_note)``.
    """
    S = mel.parse_melody(subject)
    if not S:
        raise ValueError("Fugue subject is empty.")
    A = mel.transpose_diatonic(S, 4)  # real answer, up a fifth
    CS = (mel.parse_melody(countersubject)
          if countersubject else mel.invert(S, axis_degree=1))
    material = {"S": S, "A": A}

    subj_len = sum(n.beats for n in S)
    n_entries = len(ENTRY_PLAN)
    events: list[tuple[str, float, float, int]] = []

    def emit(voice: str, line: list[mel.MelodyNote], start: float) -> None:
        lo, hi = VOICE_RANGES[voice]
        for when, dur, note in mel.realize_melody(line, key_pc, mode,
                                                  base_octave=5, lo=lo, hi=hi):
            events.append((voice, start + when, dur, note))

    # ----- exposition: one block per entry -----
    for block in range(n_entries):
        start = block * subj_len
        for idx, (voice, mat) in enumerate(ENTRY_PLAN):
            if idx > block:
                continue                       # not entered yet
            if idx == block:
                line = material[mat]           # the new entry
            elif idx == block - 1:
                line = CS                       # countersubject just after entry
            else:
                line = _free_line(block, idx, subj_len)
            emit(voice, line, start)

    # ----- cadence -----
    cad_start = n_entries * subj_len
    cad = _cadence(subj_len)
    cad_len = max(sum(n.beats for n in line) for line in cad.values())
    for voice, line in cad.items():
        emit(voice, line, cad_start)

    return events, cad_start + cad_len


DEFAULT_SUBJECT = "q1 e3 e5 q3 e5 e4 e3 e2 h1"
