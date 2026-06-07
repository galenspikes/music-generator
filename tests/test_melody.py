"""Golden tests for the melody primitive (parse, scales, infer_key, realize,
transforms)."""

import pytest

import music_generator as mg
import melody as M


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

def test_parse_basic_degrees_and_durations():
    notes = M.parse_melody("q1 e3 h5")
    assert [(n.degree, n.beats) for n in notes] == [(1, 1.0), (3, 0.5), (5, 2.0)]
    assert all(n.accidental == 0 and n.octave == 0 for n in notes)


def test_parse_rest_dot_accidental_octave():
    n = M.parse_melody("qr")[0]
    assert n.is_rest and n.beats == 1.0
    n = M.parse_melody("q.1")[0]
    assert n.beats == 1.5                       # dotted quarter
    n = M.parse_melody("e#4")[0]
    assert n.degree == 4 and n.accidental == 1
    n = M.parse_melody("hb7,")[0]
    assert n.degree == 7 and n.accidental == -1 and n.octave == -1
    n = M.parse_melody("q5'")[0]
    assert n.octave == 1


def test_parse_ignores_barlines():
    notes = M.parse_melody("q1 q3 | q5 | h1")
    assert [n.degree for n in notes] == [1, 3, 5, 1]


def test_parse_operators_repeat_and_chain():
    assert [n.degree for n in M.parse_melody("q1*3")] == [1, 1, 1]
    assert [n.degree for n in M.parse_melody("[q1 q3]*2 q5")] == [1, 3, 1, 3, 5]


@pytest.mark.parametrize("bad", ["q8", "x1", "q", "q1#", "h9", "q0"])
def test_parse_errors(bad):
    with pytest.raises(ValueError):
        M.parse_melody(bad)


# --------------------------------------------------------------------------
# key inference
# --------------------------------------------------------------------------

def _seq(keys: str):
    roots = mg.key_roots("ostinato", keys)
    return mg.build_progression(roots, ["triads"], "roundrobin",
                                max_chords=len(roots))


def test_infer_key_major():
    assert M.infer_key(_seq("C::maj, F::maj, G::maj, C::maj")) == (0, "major")


def test_infer_key_minor():
    # A C E / D F A / E G B / A C E -> A minor (final + frequent root = A)
    assert M.infer_key(_seq("A::min, D::min, E::min, A::min")) == (9, "minor")


def test_infer_key_empty():
    assert M.infer_key([]) == (0, "major")


# --------------------------------------------------------------------------
# transforms
# --------------------------------------------------------------------------

def test_transpose_diatonic():
    out = M.transpose_diatonic(M.parse_melody("q1 q3"), 1)
    assert [n.degree for n in out] == [2, 4]
    # a 5th up (+4 steps) turns 1 -> 5
    assert M.transpose_diatonic(M.parse_melody("q1"), 4)[0].degree == 5


def test_transpose_wraps_octave():
    out = M.transpose_diatonic(M.parse_melody("q6"), 3)  # idx5+3=8 -> deg2, +1 oct
    assert out[0].degree == 2 and out[0].octave == 1


def test_invert_around_tonic():
    # 5 above tonic inverts to the 4 an octave below
    out = M.invert(M.parse_melody("q5"), axis_degree=1)
    assert out[0].degree == 4 and out[0].octave == -1
    # axis note maps to itself
    assert M.invert(M.parse_melody("q3"), axis_degree=3)[0].degree == 3


def test_retrograde():
    out = M.retrograde(M.parse_melody("q1 e3 h5"))
    assert [(n.degree, n.beats) for n in out] == [(5, 2.0), (3, 0.5), (1, 1.0)]


def test_augment_and_diminish():
    assert [n.beats for n in M.augment(M.parse_melody("q1 e3"), 2.0)] == [2.0, 1.0]
    assert [n.beats for n in M.augment(M.parse_melody("q1"), 0.5)] == [0.5]


# --------------------------------------------------------------------------
# realization
# --------------------------------------------------------------------------

def test_realize_key_relative_pitch_classes():
    notes = M.parse_melody("q1 q3 q5")          # in C major -> C E G
    out = M.realize_melody(notes, key_pc=0, mode="major", lo=48, hi=84)
    assert [n % 12 for _, _, n in out] == [0, 4, 7]
    assert [w for w, _, _ in out] == [0.0, 1.0, 2.0]
    assert [d for _, d, _ in out] == [1.0, 1.0, 1.0]


def test_realize_accidental_and_octave_in_range():
    out = M.realize_melody(M.parse_melody("q#1 q1'"), key_pc=0, mode="major",
                           lo=48, hi=84)
    assert out[0][2] % 12 == 1                   # C# (raised tonic)
    assert all(48 <= n <= 84 for _, _, n in out)


def test_realize_chord_relative_transposes_motif():
    # motif "1 3 5" over a C-then-G span, in C major, chord-relative:
    # on C -> C E G (pcs 0,4,7); on G (degree 5) -> shift +4 -> 5 7 2 (G B D)
    notes = M.parse_melody("q1 q3 q5 q1 q3 q5")
    spans = [(0.0, 3.0, 0), (3.0, 6.0, 7)]       # C for 3 beats, then G
    out = M.realize_melody(notes, key_pc=0, mode="major", lo=48, hi=84,
                           relative="chord", chord_roots=spans)
    pcs = [n % 12 for _, _, n in out]
    assert pcs[:3] == [0, 4, 7]                  # over C
    assert pcs[3:] == [7, 11, 2]                 # over G: G B D
