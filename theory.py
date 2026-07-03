# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""Pitch-class set analysis for the chord recipes.

Turns a recipe's semitone offsets (see ``library/chord_recipes.py``) into the
standard theoretic descriptors: pitch-class set, normal form, prime form,
interval-class vector, Forte number, the stacked-interval reading, root-relative
degree labels, and a few derived "character" flags (symmetry, whole-tone /
octatonic subsets, quartal stacks, …).

Everything except the Forte lookup is computed from first principles, so the
prime forms and interval-class vectors are correct by construction. The Forte
numbers come from ``SET_CLASSES`` (the 42 set classes the catalogue actually
uses) and are pinned by anchors in ``tests/test_theory.py``. Prime forms use the
Rahn / "most packed to the left" convention.

Sources for the method (see docs/reference/chord-recipes.md for the full
bibliography that the generated pages footnote against):
  [1] Allen Forte, *The Structure of Atonal Music* (New Haven: Yale University
      Press, 1973) — set-class names ("Forte numbers") and the interval-class
      vector.
  [2] John Rahn, *Basic Atonal Theory* (New York: Longman, 1980) — the prime-form
      ("most packed to the left") selection used here.
  [3] Joseph N. Straus, *Introduction to Post-Tonal Theory*, 4th ed. (New York:
      W. W. Norton, 2016) — normal-form / prime-form procedure.
"""
from __future__ import annotations

from itertools import combinations

LETTER_NAMES = ["C", "D", "E", "F", "G", "A", "B"]
LETTER_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# Consecutive-interval names (semitones -> quality), including compound steps.
_INTERVAL_NAMES = {
    0: "P1", 1: "m2", 2: "M2", 3: "m3", 4: "M3", 5: "P4", 6: "TT",
    7: "P5", 8: "m6", 9: "M6", 10: "m7", 11: "M7", 12: "P8",
    13: "m9", 14: "M9", 15: "m10", 16: "M10", 17: "P11", 18: "TT+8",
    19: "P12", 20: "m13", 21: "M13", 22: "m14",
}

# Raw offset -> (degree label, diatonic-step index 0..6 relative to the root
# letter). The step index drives enharmonic spelling; the label is what a
# player reads (R, ♭3, ♯11, …). Register is honoured: a low 5 is the 4th, a high
# 17 is the 11th; a low 9 is the 6th, a high 21 is the 13th.
_DEGREE = {
    0: ("R", 0), 1: ("♭9", 1), 2: ("2", 1), 3: ("♭3", 2), 4: ("3", 2),
    5: ("4", 3), 6: ("♭5", 4), 7: ("5", 4), 8: ("♯5", 4), 9: ("6", 5),
    10: ("♭7", 6), 11: ("7", 6), 12: ("8", 0), 13: ("♭9", 1), 14: ("9", 1),
    15: ("♯9", 1), 16: ("♭11", 3), 17: ("11", 3), 18: ("♯11", 3),
    19: ("♯12", 4), 20: ("♭13", 5), 21: ("13", 5), 22: ("♯13", 5),
}

# Forte number for every set class that appears in the catalogue (42 total).
# Keyed by prime form (Rahn). Values validated against known anchors in tests.
SET_CLASSES: dict[tuple[int, ...], str] = {
    (0, 5): "2-5",
    (0, 1, 2): "3-1", (0, 2, 6): "3-8", (0, 2, 7): "3-9",
    (0, 3, 6): "3-10", (0, 3, 7): "3-11", (0, 4, 8): "3-12",
    (0, 1, 2, 3): "4-1", (0, 1, 3, 7): "4-Z29", (0, 1, 4, 6): "4-Z15",
    (0, 1, 4, 7): "4-18", (0, 1, 4, 8): "4-19", (0, 1, 5, 6): "4-8",
    (0, 1, 5, 7): "4-16", (0, 1, 5, 8): "4-20", (0, 2, 3, 7): "4-14",
    (0, 2, 4, 6): "4-21", (0, 2, 4, 7): "4-22", (0, 2, 4, 8): "4-24",
    (0, 2, 5, 7): "4-23", (0, 2, 5, 8): "4-27", (0, 2, 6, 8): "4-25",
    (0, 3, 4, 7): "4-17", (0, 3, 5, 8): "4-26", (0, 3, 6, 9): "4-28",
    (0, 1, 2, 3, 4): "5-1", (0, 1, 3, 5, 8): "5-27", (0, 1, 3, 6, 9): "5-31",
    (0, 1, 4, 5, 8): "5-21", (0, 1, 4, 6, 9): "5-32", (0, 1, 5, 6, 8): "5-20",
    (0, 2, 3, 5, 7): "5-23", (0, 2, 3, 6, 8): "5-28", (0, 2, 4, 5, 8): "5-26",
    (0, 2, 4, 6, 9): "5-34", (0, 2, 4, 7, 9): "5-35",
    (0, 1, 3, 5, 6, 8): "6-Z25", (0, 1, 3, 5, 7, 9): "6-34",
    (0, 2, 3, 5, 7, 9): "6-33", (0, 2, 4, 5, 7, 9): "6-32",
    (0, 2, 4, 6, 8, 10): "6-35",
    (0, 1, 3, 4, 6, 8, 10): "7-34",
}

_OCTATONIC = [
    frozenset({0, 1, 3, 4, 6, 7, 9, 10}),
    frozenset({1, 2, 4, 5, 7, 8, 10, 11}),
    frozenset({2, 3, 5, 6, 8, 9, 11, 0}),
]

# Aggregate dyadic consonance weights per interval class ic1..ic6, from
# David Huron, "Interval-Class Content in Equally Tempered Pitch-Class Sets"
# (Music Perception 11/3, 1994). Higher = more consonant. Used to rank chords
# on a consonant..dissonant axis in the reference.
HURON_WEIGHTS = [-1.428, -0.582, 0.594, 0.386, 1.240, -0.453]
_H_LO, _H_HI = min(HURON_WEIGHTS), max(HURON_WEIGHTS)
_CONSONANCE_BANDS = [(0.28, "consonant"), (0.42, "mild"), (0.58, "tense"),
                     (0.75, "dissonant"), (1.01, "harsh")]


def pitch_classes(offsets: list[int]) -> list[int]:
    """Sorted, de-duplicated pitch-class set (mod 12)."""
    return sorted({o % 12 for o in offsets})


def interval_class_vector(pcs: list[int]) -> list[int]:
    """The six interval classes counted across all pairs (ic1…ic6)."""
    vec = [0, 0, 0, 0, 0, 0]
    for a, b in combinations(sorted(set(pcs)), 2):
        d = abs(a - b)
        vec[min(d, 12 - d) - 1] += 1
    return vec


def consonance(pcs: list[int]) -> dict:
    """Rate the chord on a consonant..dissonant axis via Huron's aggregate
    dyadic consonance. Returns the mean per-dyad ``score`` (Huron units), a
    normalised dissonance ``index`` (0 consonant .. 1 dissonant), a ``band``
    label, and a plain-language ``reading`` of the sharp dissonances."""
    icv = interval_class_vector(pcs)
    pairs = sum(icv)
    if pairs == 0:
        return {"score": 0.0, "index": 0.0, "band": "—", "reading": "a single tone"}
    score = sum(w * c for w, c in zip(HURON_WEIGHTS, icv)) / pairs
    index = (_H_HI - score) / (_H_HI - _H_LO)
    band = next(name for hi, name in _CONSONANCE_BANDS if index < hi)
    parts = []
    if icv[0]:
        parts.append(f"{icv[0]} semitone{'s' if icv[0] != 1 else ''}")
    if icv[5]:
        parts.append(f"{icv[5]} tritone{'s' if icv[5] != 1 else ''}")
    reading = ", ".join(parts) if parts else "no semitones or tritones"
    return {"score": round(score, 3), "index": round(index, 3),
            "band": band, "reading": reading}


def normal_form(pcs: list[int]) -> list[int]:
    """Most compact rotation (Straus): smallest span, packed from the left,
    final ties broken by the lowest starting pitch class."""
    pcs = sorted(set(pcs))
    n = len(pcs)
    if n < 2:
        return pcs[:]
    best = None
    for i in range(n):
        rot = [pcs[(i + k) % n] % 12 for k in range(n)]
        spans = [(rot[k] - rot[0]) % 12 for k in range(n)]
        # compare spans from the outside in, then the starting pc
        key = tuple(spans[j] for j in range(n - 1, 0, -1)) + (rot[0],)
        if best is None or key < best[0]:
            best = (key, rot)
    return best[1]


def _transpose_to_zero(pcs: list[int]) -> list[int]:
    return [(p - pcs[0]) % 12 for p in pcs]


def prime_form(pcs: list[int]) -> list[int]:
    """Rahn prime form: the more left-packed of the set's and its inversion's
    normal forms, each transposed to begin on 0."""
    pcs = sorted(set(pcs))
    if not pcs:
        return []
    original = _transpose_to_zero(normal_form(pcs))
    inverted = _transpose_to_zero(normal_form([(-p) % 12 for p in pcs]))
    return min(original, inverted)


def forte_number(pcs: list[int]) -> str | None:
    """Forte set-class name, or ``None`` if the set class isn't catalogued."""
    return SET_CLASSES.get(tuple(prime_form(pcs)))


def transpositional_symmetry(pcs: list[int]) -> int:
    """How many transpositions (Tn, n≠0) map the set onto itself."""
    s = frozenset(p % 12 for p in pcs)
    return sum(1 for n in range(1, 12) if {(p + n) % 12 for p in s} == s)


def inversional_symmetry(pcs: list[int]) -> bool:
    """True when some inversion (TnI) maps the set onto itself."""
    s = frozenset(p % 12 for p in pcs)
    return any({(n - p) % 12 for p in s} == s for n in range(12))


def is_quartal(pcs: list[int]) -> bool:
    """True when the set is a chain of perfect fourths (or fifths)."""
    s = frozenset(pcs)
    n = len(s)
    if n < 3:
        return False
    return any({(b + 5 * k) % 12 for k in range(n)} == s for b in s)


def _subset_of_wholetone(pcs: list[int]) -> bool:
    return len({p % 2 for p in pcs}) == 1


def _subset_of_octatonic(pcs: list[int]) -> bool:
    s = set(p % 12 for p in pcs)
    return any(s <= oct_ for oct_ in _OCTATONIC)


def character_flags(offsets: list[int]) -> list[str]:
    """Human-readable structural tags derived from the set (order = priority)."""
    pcs = pitch_classes(offsets)
    icv = interval_class_vector(pcs)
    flags: list[str] = []
    if transpositional_symmetry(pcs):
        flags.append("transpositionally symmetric")
    if inversional_symmetry(pcs):
        flags.append("inversionally symmetric")
    if list(prime_form(pcs)) == list(range(len(pcs))):
        flags.append("chromatic cluster")
    if is_quartal(pcs):
        flags.append("quartal / quintal")
    if len(pcs) >= 3 and _subset_of_wholetone(pcs):
        flags.append("whole-tone subset")
    if len(pcs) >= 4 and _subset_of_octatonic(pcs):
        flags.append("octatonic subset")
    if forte_number(pcs) in ("4-Z15", "4-Z29"):
        flags.append("all-interval tetrachord")
    if icv[5] == 0:
        flags.append("tritone-free")
    elif icv[5] >= 2:
        flags.append("multiple tritones")
    return flags


def _spell(pc: int, step: int, root_pc: int, root_letter: str) -> str:
    """Enharmonic note name for ``pc`` as diatonic ``step`` above the root."""
    letter = LETTER_NAMES[(LETTER_NAMES.index(root_letter) + step) % 7]
    acc = ((pc - LETTER_PC[letter] + 6) % 12) - 6  # nearest, in [-6, 5]
    if acc <= -3:
        acc += 12
    if acc >= 3:
        acc -= 12
    mark = ("𝄫" if acc == -2 else "♭" if acc == -1
            else "♯" if acc == 1 else "𝄪" if acc == 2 else "")
    return letter + mark


def stacked_intervals(offsets: list[int]) -> list[str]:
    """Interval names between consecutive chord tones, bottom to top."""
    ordered = sorted(offsets)
    out = []
    for a, b in zip(ordered, ordered[1:]):
        d = b - a
        out.append(_INTERVAL_NAMES.get(d, f"{d}st"))
    return out


def degree_label(offset: int) -> str:
    """Root-relative degree label for a raw offset (R, ♭3, ♯11, …)."""
    lab = _DEGREE.get(offset)
    if lab:
        return lab[0]
    return _DEGREE.get(offset % 12, ("?", 0))[0]


def analyze(offsets: list[int], root_pc: int = 0,
            root_letter: str = "C") -> dict:
    """Full analysis record for one recipe's offsets over a chosen root."""
    pcs = pitch_classes(offsets)
    pf = prime_form(pcs)
    notes = []
    for off in sorted(offsets):
        lab, step = _DEGREE.get(off, _DEGREE.get(off % 12, ("?", 0)))
        pc = (root_pc + off) % 12
        notes.append({
            "offset": off,
            "pc": pc,
            "degree": lab,
            "step": step,
            "name": _spell(pc, step, root_pc, root_letter),
        })
    return {
        "offsets": list(offsets),
        "pcs": pcs,
        "notes": notes,
        "cardinality": len(pcs),
        "normal_form": normal_form(pcs),
        "prime_form": pf,
        "prime_str": "[" + " ".join(str(p) for p in pf) + "]",
        "forte": forte_number(pcs),
        "icv": interval_class_vector(pcs),
        "intervals": stacked_intervals(offsets),
        "flags": character_flags(offsets),
        "consonance": consonance(pcs),
    }
