"""Tests for the lead/hook generator (lead.py, roadmap Thread 2 v1+v2)."""

import random

import pytest

import lead as L
from mtheory import ChordDef

# Two-chord vamp: C major and G major, 8 beats each -> a 16-beat section.
CMAJ = ChordDef(root_pc=0, pcs=(0, 4, 7))
GMAJ = ChordDef(root_pc=7, pcs=(7, 11, 2))
SPANS = [(0.0, 8.0, CMAJ), (8.0, 16.0, GMAJ)]


def _build(seed=1, **kwargs):
    random.seed(seed)
    return L.build_lead_events(SPANS, key_pc=0, mode="major", **kwargs)


def test_empty_spans_yield_no_events():
    assert L.build_lead_events([], 0, "major") == []


def test_deterministic_under_seed():
    assert _build(seed=7) == _build(seed=7)


def test_events_stay_inside_the_section():
    events = _build()
    assert events
    for when, dur, _note in events:
        assert 0.0 <= when < 16.0
        assert when + dur <= 16.0 + 1e-9


def test_events_are_monophonic_and_ordered():
    events = _build()
    for (w1, d1, _), (w2, _, _) in zip(events, events[1:]):
        assert w2 >= w1 + d1 - 1e-9  # next onset never before current release


def test_register_bounds_respected():
    for register, (lo, hi) in L.LEAD_REGISTERS.items():
        events = _build(seed=3, register=register)
        assert events, register
        assert all(lo <= n <= hi for _, _, n in events), register


def test_strong_beats_are_chord_tones():
    events = _build(seed=5)
    for when, _dur, note in events:
        if when % 2.0 < 1e-6:
            chord = CMAJ if when < 8.0 else GMAJ
            assert note % 12 in chord.pcs, (when, note)


def test_final_note_is_a_chord_tone():
    events = _build(seed=9)
    when, _dur, note = events[-1]
    chord = CMAJ if when < 8.0 else GMAJ
    assert note % 12 in chord.pcs


def test_user_motif_intervals_survive_realization():
    # An authored stepwise line on weak beats must keep its exact intervals
    # (regression: pc-nearest octave placement used to turn steps into drops).
    # A sixteenth-rest pickup puts every onset at x.25/x.75 — no strong beats,
    # so no chord snapping; C major degrees 1 2 3 4 = +2 +2 +1 semitones.
    events = _build(seed=1, motif_text="sr e1 e2 e3 e4", rests=1.0)
    first = [n for w, _, n in events if w < 4.0]
    assert [b - a for a, b in zip(first, first[1:])] == [2, 2, 1]


def test_user_motif_rhythm_is_stated_verbatim():
    # First phrase must reproduce the authored motif's onsets exactly.
    events = _build(seed=1, motif_text="q1 q3 q5 qr")
    first_bar = [(w, d) for w, d, _ in events if w < 4.0]
    assert first_bar == [(0.0, 1.0), (1.0, 1.0), (2.0, 1.0)]


def test_rests_one_silences_every_response_phrase():
    events = _build(seed=2, rests=1.0)
    # phrase slots are 4 beats; slot 1 (beats 4-8) is the response slot
    assert not any(4.0 <= w < 8.0 for w, _, _ in events)


def test_rests_zero_fills_response_phrase():
    events = _build(seed=2, rests=0.0)
    assert any(4.0 <= w < 8.0 for w, _, _ in events)


def test_generated_motif_density_tiers():
    random.seed(4)
    sparse = L.generate_motif(0.1)
    random.seed(4)
    busy = L.generate_motif(0.9)
    n_sparse = sum(1 for n in sparse if not n.is_rest)
    n_busy = sum(1 for n in busy if not n.is_rest)
    assert n_busy > n_sparse
    # every cell tiles exactly one phrase bar
    assert sum(n.beats for n in sparse) == pytest.approx(L.PHRASE_BEATS)
    assert sum(n.beats for n in busy) == pytest.approx(L.PHRASE_BEATS)


def test_development_varies_the_line():
    # With a fixed motif over changing chords, later phrases should not all
    # be pitch-identical to the first (transpose/invert/sequence devices).
    events = _build(seed=6, motif_text="q1 q2 q3 qr", rests=0.0)
    bar = lambda k: [n for w, _, n in events if k * 4.0 <= w < (k + 1) * 4.0]  # noqa: E731
    assert bar(0), "statement phrase missing"
    others = [bar(k) for k in range(1, 4) if bar(k)]
    assert others, "no later phrases generated"
    assert any(b != bar(0) for b in others)
