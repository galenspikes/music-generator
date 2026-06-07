"""Melody primitive: a scale-degree mini-language + model + transforms.

Shared foundation for the (future) fugue subject handling and the lead/hook
generator. Pitch is written as scale degrees relative to a key+mode, so the
fugal operations (answer, inversion, retrograde, augmentation) are clean
transforms; realization to MIDI happens last, given a key/mode/register.

Grammar (whitespace-separated, '|' barlines ignored; ',' = octave down):
    <dur>[.] ( [#|b]<1-7>['|,]* | r )
e.g.  "q1 q5 e5 e4 q3 | h2 q1 qr"   "q.1 e5 q3' e#7, h1"
Operators reuse the DSL feel: token*N and [ ... ]*N chains.

See docs/melody-primitive-plan.md.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

import music_generator as mg

DUR_MAP = mg.DUR_MAP  # w h q e s t

# Scale interval sets (semitones from the tonic).
SCALES: dict[str, list[int]] = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],          # natural minor
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
}
SCALES["ionian"] = SCALES["major"]
SCALES["aeolian"] = SCALES["minor"]

# Modes considered by inference (small set = fewer mis-guesses).
INFER_MODES = ("major", "minor", "dorian", "mixolydian")


@dataclass(frozen=True)
class MelodyNote:
    degree: int | None    # 1..7, or None for a rest
    accidental: int       # -1, 0, +1
    octave: int           # relative octave offset
    beats: float
    is_rest: bool = False


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

_TOKEN_RE = re.compile(
    r"^(?P<dur>[whqest])(?P<dot>\.?)"
    r"(?:(?P<rest>r)|(?P<acc>[#b]?)(?P<deg>[1-7])(?P<oct>['\,]*))$")


def parse_single_melody_token(tok: str) -> MelodyNote:
    m = _TOKEN_RE.match(tok.strip())
    if not m:
        raise ValueError(f"Bad melody token '{tok}'")
    beats = DUR_MAP[m.group("dur")] * (1.5 if m.group("dot") else 1.0)
    if m.group("rest"):
        return MelodyNote(None, 0, 0, beats, True)
    acc = {"#": 1, "b": -1, "": 0}[m.group("acc")]
    octs = m.group("oct")
    octave = octs.count("'") - octs.count(",")
    return MelodyNote(int(m.group("deg")), acc, octave, beats, False)


def _expand_operators(text: str) -> list[str]:
    text = text.replace("|", " ")

    def _chain(match: re.Match) -> str:
        inner, count = match.group(1).strip(), int(match.group(2))
        return (" " + inner + " ") * count

    text = re.sub(r"\[([^\]]*)\]\*(\d+)", _chain, text)

    # Whitespace-separated only: ',' is the octave-down mark (Lilypond/ABC style).
    out: list[str] = []
    for raw in re.split(r"\s+", text.strip()):
        if not raw:
            continue
        rep = re.match(r"^(.*?)\*(\d+)$", raw)
        if rep:
            out.extend([rep.group(1)] * int(rep.group(2)))
        else:
            out.append(raw)
    return out


def parse_melody(text: str) -> list[MelodyNote]:
    """Parse a melody string into a list of MelodyNote (mirrors parse_pattern)."""
    return [parse_single_melody_token(t) for t in _expand_operators(text)]


# --------------------------------------------------------------------------
# Scales / key inference
# --------------------------------------------------------------------------

def scale_for(mode: str) -> list[int]:
    key = mode.strip().lower()
    if key not in SCALES:
        raise ValueError(f"Unknown mode '{mode}'")
    return SCALES[key]


def infer_key(chord_seq, modes: tuple[str, ...] = INFER_MODES) -> tuple[int, str]:
    """Infer (tonic_pc, mode) from a chord sequence (list of ChordDef).

    Heuristic: score each (tonic, mode) by how well its scale covers the used
    pitch classes, with tonic cues from the final/most-frequent chord root.
    Mis-guesses on modal/chromatic charts are expected — callers should allow an
    explicit override.
    """
    if not chord_seq:
        return (0, "major")

    pc_weight: Counter = Counter()
    root_weight: Counter = Counter()
    for ch in chord_seq:
        for pc in ch.pcs:
            pc_weight[pc % 12] += 1
        root_weight[ch.root_pc % 12] += 1

    final_root = chord_seq[-1].root_pc % 12
    best = None
    for tonic in range(12):
        for mode in modes:
            scale = {(tonic + iv) % 12 for iv in SCALES[mode]}
            in_score = sum(w for pc, w in pc_weight.items() if pc in scale)
            out_pen = sum(w for pc, w in pc_weight.items() if pc not in scale)
            score = in_score - 1.5 * out_pen
            score += 0.5 * root_weight.get(tonic, 0)
            if final_root == tonic:
                score += 2.0
            if mode in ("major", "minor"):
                score += 0.1  # nudge: prefer plain major/minor on ties
            if best is None or score > best[0]:
                best = (score, tonic, mode)
    return (best[1], best[2])


# --------------------------------------------------------------------------
# Transforms (degree space)
# --------------------------------------------------------------------------

def _shift_degree(note: MelodyNote, steps: int) -> MelodyNote:
    if note.is_rest or note.degree is None:
        return note
    idx = (note.degree - 1) + steps
    octave = note.octave + idx // 7
    return MelodyNote(idx % 7 + 1, note.accidental, octave, note.beats, False)


def transpose_diatonic(notes: list[MelodyNote], steps: int) -> list[MelodyNote]:
    """Shift every note by N scale steps (the fugal answer = +3 for a 4th,
    +4 for a 5th). Rests pass through."""
    return [_shift_degree(n, steps) for n in notes]


def invert(notes: list[MelodyNote], axis_degree: int = 1) -> list[MelodyNote]:
    """Melodic inversion: reflect each degree about an axis degree."""
    axis = axis_degree - 1
    out = []
    for n in notes:
        if n.is_rest or n.degree is None:
            out.append(n)
            continue
        idx = 2 * axis - (n.degree - 1)
        octave = n.octave + idx // 7
        out.append(MelodyNote(idx % 7 + 1, -n.accidental, octave, n.beats, False))
    return out


def retrograde(notes: list[MelodyNote]) -> list[MelodyNote]:
    """Reverse the note order (rhythm reverses with it)."""
    return list(reversed(notes))


def augment(notes: list[MelodyNote], factor: float = 2.0) -> list[MelodyNote]:
    """Scale all durations (factor>1 augments, <1 diminishes)."""
    return [
        MelodyNote(n.degree, n.accidental, n.octave, n.beats * factor, n.is_rest)
        for n in notes
    ]


# --------------------------------------------------------------------------
# Realization to MIDI
# --------------------------------------------------------------------------

def _degree_pc(note: MelodyNote, key_pc: int, scale: list[int]) -> int:
    interval = scale[(note.degree - 1) % 7] + note.accidental
    return (key_pc + interval + 12 * note.octave)


def _root_degree_in_scale(root_pc: int, key_pc: int, scale: list[int]) -> int:
    """Diatonic step (0-based) of root_pc within the key's scale; nearest if the
    root is chromatic (not strictly in scale)."""
    rel = (root_pc - key_pc) % 12
    if rel in scale:
        return scale.index(rel)
    return min(range(7), key=lambda i: min((scale[i] - rel) % 12,
                                           (rel - scale[i]) % 12))


def realize_melody(notes: list[MelodyNote],
                   key_pc: int,
                   mode: str,
                   base_octave: int = 5,
                   lo: int = 55,
                   hi: int = 84,
                   relative: str = "key",
                   chord_roots: list[tuple[float, float, int]] | None = None
                   ) -> list[tuple[float, float, int]]:
    """Realize a melody to ``[(when_beats, dur_beats, midi_note)]``.

    relative="key": degrees resolve against the section scale (constant).
    relative="chord": each note is diatonically transposed so degree 1 lands on
        the current chord's root (chord_roots = [(start, end, root_pc)] spans in
        the same beat frame). A motif then auto-fits each chord.
    """
    scale = scale_for(mode)
    out: list[tuple[float, float, int]] = []
    when = 0.0
    for note in notes:
        dur = note.beats
        if note.is_rest or note.degree is None:
            when += dur
            continue
        eff = note
        if relative == "chord" and chord_roots:
            root = _root_at(chord_roots, when)
            if root is not None:
                shift = _root_degree_in_scale(root, key_pc, scale)
                eff = _shift_degree(note, shift)
        target = _degree_pc(eff, key_pc, scale) + 12 * base_octave
        note = mg.clamp_to_range(mg.nearest_in_register(target, lo, hi), lo, hi)
        out.append((when, dur, note))
        when += dur
    return out


def _root_at(spans: list[tuple[float, float, int]], when: float) -> int | None:
    for start, end, root in spans:
        if start <= when < end:
            return root
    return spans[-1][2] if spans else None
