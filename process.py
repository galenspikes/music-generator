"""Process-music generator: phasing, additive, and augmentation.

Minimalist/process techniques applied to a melodic cell (written in the melody
mini-language), unfolding by rule over time:

- **phase** (Reich, *Piano Phase*): two voices loop the cell; the follower
  advances one note per stage, sweeping through every alignment and back to
  unison.
- **additive** (Glass): the cell grows a note at a time (1, 12, 123, …) then
  contracts.
- **augment** (Reich, *Four Organs*): the cell's durations lengthen each stage.

Stands on the melody primitive (`melody.py`) and the four voice-channels.
"""

from __future__ import annotations

import melody as mel
import music_generator as mg

PROCESS_KINDS = ("phase", "additive", "augment")

VOICE_RANGES = {
    "soprano": mg.SOP_RANGE,
    "alto": mg.ALTO_RANGE,
    "tenor": mg.TENOR_RANGE,
    "bass": mg.BASS_RANGE,
}

# A compact, phase-friendly cell (uniform eighths so rotation == time-shift).
DEFAULT_CELL = "e1 e2 e3 e5 e6 e5 e3 e2"


def _emit(events, voice, line, start, key_pc, mode):
    lo, hi = VOICE_RANGES[voice]
    for when, dur, note in mel.realize_melody(line, key_pc, mode,
                                              base_octave=5, lo=lo, hi=hi):
        events.append((voice, start + when, dur, note))


def _rotate(cell, s):
    s %= len(cell)
    return cell[s:] + cell[:s]


def build_process(cell_text: str,
                  key_pc: int,
                  mode: str,
                  kind: str = "phase",
                  reps: int = 4,
                  stages: int = 6,
                  voices: tuple[str, str] = ("soprano", "alto"),
                  augment_amount: float = 0.5
                  ) -> tuple[list[tuple[str, float, float, int]], float]:
    """Build a process piece. Returns ``(events, total_beats)`` where each event
    is ``(voice_name, when_beats, dur_beats, midi_note)``."""
    if kind not in PROCESS_KINDS:
        raise ValueError(f"Unknown process kind '{kind}'")
    cell = mel.parse_melody(cell_text)
    if not cell:
        raise ValueError("Process cell is empty.")
    cell_beats = sum(n.beats for n in cell)
    events: list[tuple[str, float, float, int]] = []
    t = 0.0

    if kind == "phase":
        va, vb = voices
        # s = 0 (unison) .. len(cell) (back to unison): follower advances 1/stage
        for s in range(len(cell) + 1):
            for _ in range(reps):
                _emit(events, va, cell, t, key_pc, mode)
                _emit(events, vb, _rotate(cell, s), t, key_pc, mode)
                t += cell_beats

    elif kind == "additive":
        v = voices[0]
        grow = list(range(1, len(cell) + 1))
        shrink = list(range(len(cell) - 1, 0, -1))
        for k in grow + shrink:
            sub = cell[:k]
            sub_beats = sum(n.beats for n in sub)
            for _ in range(reps):
                _emit(events, v, sub, t, key_pc, mode)
                t += sub_beats

    else:  # augment
        v = voices[0]
        for k in range(stages):
            factor = 1.0 + k * augment_amount
            aug = mel.augment(cell, factor)
            aug_beats = sum(n.beats for n in aug)
            for _ in range(reps):
                _emit(events, v, aug, t, key_pc, mode)
                t += aug_beats

    return events, t
