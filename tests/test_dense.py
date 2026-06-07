"""Tests for dense voicing (sound every chord tone, not just 4)."""

import music_generator as mg


def _chord(sym):
    c = mg.parse_colon_key_token(sym)
    return c, mg.realize_dense(c.root_pc, list(c.pcs), c.bass_pc)


def test_dense_sounds_all_pitch_classes_of_a_13th():
    c, notes = _chord("C::13")          # C E G Bb D A -> 6 pcs
    pcs_in_chord = {p % 12 for p in c.pcs}
    pcs_voiced = {n % 12 for n in notes}
    assert pcs_in_chord <= pcs_voiced   # every chord tone is present
    assert len(notes) >= len(pcs_in_chord)


def test_dense_exceeds_four_voices_for_rich_chords():
    _, notes = _chord("C::messiaen_resonance")   # 7-tone set
    assert len(notes) > 4


def test_dense_is_a_spread_ascending_stack():
    _, notes = _chord("C::maj9")
    assert notes == sorted(notes)
    assert notes[-1] - notes[0] >= 12          # spans at least an octave


def test_dense_respects_slash_bass_at_bottom():
    c, notes = _chord("G::maj/C")
    assert notes[0] % 12 == 0                   # C in the bass


def test_dense_stays_in_register():
    for sym in ("C::maj", "E::mystic", "F::13", "D::quartal"):
        _, notes = _chord(sym)
        assert all(36 <= n <= 88 for n in notes), sym
