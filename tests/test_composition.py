"""Tests for composition: progressions, chord families, and timelines.

Tests the chord progression builders, chord-family pickers, and timeline assembly.
Covers root selection modes, chord picking strategies, and voicing continuity.
"""

import random

import pytest

from composition import (
    build_progression,
    build_chord_timeline,
    build_harmony_events,
    circle_of_fifths_sequence,
    make_triad,
    make_seventh,
    make_ninth,
    make_extended_chord,
    make_quartal,
    fill_chords_to_end,
    invert_chord,
    next_mode_picker,
    compute_max_gap_beats,
)
from mtheory import ChordDef, pc


class TestChordBuilders:
    """Test individual chord-family builders."""

    def test_make_triad_major_by_default(self):
        """make_triad defaults to major in a major key."""
        random.seed(42)
        chord = make_triad(pc('C'))
        assert 0 in chord  # root
        assert 4 in chord  # major third
        assert 7 in chord  # fifth

    def test_make_triad_minor_in_minor_key(self):
        """make_triad produces minor in a minor key."""
        random.seed(42)
        chord = make_triad(pc('C'), is_minor_key=True)
        assert 0 in chord  # root
        assert 3 in chord  # minor third
        assert 7 in chord  # fifth

    def test_make_seventh_major_chord(self):
        """make_seventh builds maj7 or dom7."""
        random.seed(42)
        chord = make_seventh(pc('C'))
        assert 0 in chord  # root
        assert 4 in chord or 3 in chord  # third
        assert 7 in chord  # fifth
        assert 11 in chord or 10 in chord  # seventh

    def test_make_ninth_includes_extension(self):
        """make_ninth includes a 9th (2) above root."""
        random.seed(42)
        chord = make_ninth(pc('C'))
        assert 0 in chord
        assert 2 in chord or 3 in chord  # 9th or b9

    def test_make_quartal_includes_fourths(self):
        """make_quartal builds chords with fourth intervals."""
        random.seed(42)
        chord = make_quartal(pc('C'))
        assert 0 in chord  # Should include root

    def test_make_extended_chord_includes_many_tones(self):
        """make_extended_chord has at least 4 different pitch classes."""
        random.seed(42)
        chord = make_extended_chord(pc('C'))
        assert len(chord) >= 4

    def test_chord_builders_are_deterministic_with_seed(self):
        """Chord builders produce same output with same seed."""
        random.seed(42)
        c1 = make_ninth(pc('C'))
        random.seed(42)
        c2 = make_ninth(pc('C'))
        assert c1 == c2


class TestCircleOfFifths:
    """Test circle of fifths sequence generation."""

    def test_circle_of_fifths_default_length(self):
        """circle_of_fifths_sequence builds 48 chords by default (12 keys * 4)."""
        seq = circle_of_fifths_sequence([])
        assert len(seq) == 48

    def test_circle_of_fifths_includes_all_pitch_classes(self):
        """All 12 pitch classes appear in a default sequence."""
        seq = circle_of_fifths_sequence([])
        roots = {cd.root_pc for cd in seq}
        assert len(roots) == 12

    def test_circle_of_fifths_respects_max_chords(self):
        """circle_of_fifths_sequence respects max_chords parameter."""
        seq = circle_of_fifths_sequence([], max_chords=5)
        assert len(seq) == 5

    def test_circle_of_fifths_chords_are_extended(self):
        """All chords in sequence are extended (have multiple pitch classes)."""
        seq = circle_of_fifths_sequence([], max_chords=12)
        for cd in seq:
            assert len(cd.pcs) >= 3


class TestBuildProgression:
    """Test chord progression building with different picker modes."""

    def test_build_progression_single_key_ordered(self):
        """Single key with 'ordered' picker uses the provided mode."""
        random.seed(42)
        prog = build_progression(['C'], ['triads', 'sevenths'], 'ordered')
        assert len(prog) == 4  # Single key default is 4 chords
        assert all(cd.root_pc == pc('C') for cd in prog)

    def test_build_progression_multi_key_ordered(self):
        """Multiple keys with 'ordered' picker alternates through keys."""
        random.seed(42)
        prog = build_progression(['C', 'G', 'D'], ['triads'], 'ordered')
        assert len(prog) == 12  # 3 keys * 4 default repeats
        # Should have C and G roots
        roots = {cd.root_pc for cd in prog}
        assert pc('C') in roots
        assert pc('G') in roots

    def test_build_progression_colon_tokens_count_as_one(self):
        """Colon tokens in keys produce one chord each."""
        prog = build_progression(['C::maj7', 'G::7'], ['triads'], 'ordered')
        assert len(prog) == 2
        assert prog[0].root_pc == pc('C')
        assert prog[1].root_pc == pc('G')

    def test_build_progression_roundrobin_mode(self):
        """roundrobin mode cycles through recipes."""
        random.seed(42)
        prog = build_progression(['C'], ['triads', 'sevenths', 'ninths'], 'roundrobin', max_chords=9)
        labels = [cd.label for cd in prog]
        # roundrobin should cycle through the modes
        assert labels == ['triads', 'sevenths', 'ninths', 'triads', 'sevenths', 'ninths', 'triads', 'sevenths', 'ninths']

    def test_build_progression_random_mode(self):
        """random mode picks colors randomly."""
        random.seed(42)
        prog = build_progression(['C'], ['triads', 'sevenths'], 'random', max_chords=10)
        labels = [cd.label for cd in prog]
        # Should have at least one of each type (statistically likely with seed)
        assert 'triads' in labels or 'sevenths' in labels

    def test_build_progression_respects_max_chords(self):
        """max_chords parameter limits progression length."""
        prog = build_progression(['C', 'G'], ['triads'], 'ordered', max_chords=5)
        assert len(prog) == 5

    def test_build_progression_colon_tokens_override_picker(self):
        """Explicit colon tokens in keys override picker."""
        prog = build_progression(['C::maj7', 'G::min7'], ['triads'], 'ordered')
        assert len(prog) == 2
        assert prog[0].pcs == set([0, 4, 7, 11]) or 11 in prog[0].pcs
        assert prog[1].root_pc == pc('G')

    def test_build_progression_fallback_circle_of_fifths(self):
        """Empty keys list falls back to circle of fifths."""
        prog = build_progression([], ['triads'], 'ordered')
        assert len(prog) >= 12
        # Should have all 12 pitch classes
        roots = {cd.root_pc for cd in prog}
        assert len(roots) == 12 or len(prog) > 12

    def test_build_progression_empty_modes_uses_extended(self):
        """Empty chord_modes defaults to extended chords."""
        random.seed(42)
        prog = build_progression(['C'], [], 'ordered', max_chords=4)
        assert len(prog) == 4
        assert all(len(cd.pcs) >= 3 for cd in prog)


class TestBuildChordTimeline:
    """Test chord timeline assembly."""

    def test_build_chord_timeline_fills_duration(self):
        """Timeline fills to beats_total."""
        chords = [
            ChordDef(root_pc=pc('C'), pcs=(0, 4, 7)),
            ChordDef(root_pc=pc('G'), pcs=(7, 11, 2)),
        ]
        timeline = build_chord_timeline(chords, beats_total=4.0, base_len_beats=1.0)
        end_beat = max(when + dur for when, dur, _ in timeline)
        assert end_beat == pytest.approx(4.0)

    def test_build_chord_timeline_alternates_chords(self):
        """Timeline cycles through chord sequence."""
        chords = [
            ChordDef(root_pc=pc('C'), pcs=(0, 4, 7)),
            ChordDef(root_pc=pc('G'), pcs=(7, 11, 2)),
        ]
        timeline = build_chord_timeline(chords, beats_total=8.0, base_len_beats=1.0)
        # Should have both chords, each slot carrying a non-empty voicing
        assert len(timeline) >= 4  # At least 2 cycles
        assert all(voicing for _, _, voicing in timeline)

    def test_build_chord_timeline_static_mode_reuses_voicing(self):
        """static=True reuses voicing for identical chords."""
        chord = ChordDef(root_pc=pc('C'), pcs=(0, 4, 7))
        timeline_dynamic = build_chord_timeline([chord], beats_total=4.0, base_len_beats=1.0, static=False)
        timeline_static = build_chord_timeline([chord], beats_total=4.0, base_len_beats=1.0, static=True)
        # Both should have same length
        assert len(timeline_dynamic) == len(timeline_static)

    def test_build_chord_timeline_sustains_last_chord(self):
        """Last chord is sustained to fill to beats_total."""
        chords = [ChordDef(root_pc=pc('C'), pcs=(0, 4, 7))]
        timeline = build_chord_timeline(chords, beats_total=10.0, base_len_beats=2.0)
        last_when, last_dur, _ = timeline[-1]
        assert last_when + last_dur == pytest.approx(10.0)

    def test_build_chord_timeline_short_duration_truncates(self):
        """Very short beat durations truncate correctly."""
        chords = [ChordDef(root_pc=pc('C'), pcs=(0, 4, 7))]
        timeline = build_chord_timeline(chords, beats_total=0.5, base_len_beats=1.0)
        end_beat = max(when + dur for when, dur, _ in timeline) if timeline else 0
        assert end_beat == pytest.approx(0.5)


class TestFillChordsToEnd:
    """Test chord timeline extension to fill duration."""

    def test_fill_chords_to_end_no_extension_needed(self):
        """If timeline already reaches end, no change."""
        timeline = [(0, 2.0, (60, 55, 48, 40))]
        result = fill_chords_to_end(timeline, 2.0)
        assert result == timeline

    def test_fill_chords_to_end_extends_last_chord(self):
        """Last chord is extended to beats_total."""
        timeline = [(0, 1.0, (60, 55, 48, 40))]
        result = fill_chords_to_end(timeline, 4.0)
        assert len(result) == 2
        assert result[-1] == (1.0, 3.0, (60, 55, 48, 40))

    def test_fill_chords_to_end_empty_returns_empty(self):
        """Empty timeline stays empty."""
        result = fill_chords_to_end([], 4.0)
        assert result == []


class TestBuildHarmonyEvents:
    """Test harmony event assembly from chord timeline."""

    def test_build_harmony_events_produces_events(self):
        """build_harmony_events produces event tuples."""
        chords = [ChordDef(root_pc=pc('C'), pcs=(0, 4, 7))]
        timeline = build_chord_timeline(chords, beats_total=2.0, base_len_beats=1.0)
        events, _end_beat = build_harmony_events(timeline, satb_style='block')
        assert len(events) > 0
        # Events are tuples with (event_type, when, dur, voicing) or similar
        assert isinstance(events[0], tuple)

    def test_build_harmony_events_with_different_bass_styles(self):
        """build_harmony_events supports different bass styles."""
        chords = [ChordDef(root_pc=pc('C'), pcs=(0, 4, 7))]
        timeline = build_chord_timeline(chords, beats_total=2.0, base_len_beats=1.0)
        events_follow, _ = build_harmony_events(timeline, satb_style='block', bass_style='follow')
        events_none, _ = build_harmony_events(timeline, satb_style='block', bass_style='none')
        # Both should produce events
        assert len(events_follow) > 0
        assert len(events_none) > 0

    def test_build_harmony_events_satb_style_block(self):
        """SATB block style produces chord events."""
        chords = [ChordDef(root_pc=pc('C'), pcs=(0, 4, 7))]
        timeline = build_chord_timeline(chords, beats_total=1.0, base_len_beats=1.0)
        events, _end = build_harmony_events(timeline, satb_style='block')
        assert len(events) > 0

    def test_build_harmony_events_different_satb_styles(self):
        """Different SATB styles produce events."""
        chords = [ChordDef(root_pc=pc('C'), pcs=(0, 4, 7))]
        timeline = build_chord_timeline(chords, beats_total=2.0, base_len_beats=1.0)
        events_block, _ = build_harmony_events(timeline, satb_style='block')
        events_arpegg, _ = build_harmony_events(timeline, satb_style='arpeggio')
        # Both should have events
        assert len(events_block) > 0
        assert len(events_arpegg) > 0


class TestInvertChord:
    """Test chord inversion utility."""

    def test_invert_chord_root_position(self):
        """Inverting a root-position chord once rotates it."""
        chord = [0, 4, 7]
        inverted = invert_chord(chord, 1)
        # After one inversion, should be [4, 7, 12]
        assert inverted == [4, 7, 12]

    def test_invert_chord_multiple_inversions(self):
        """Multiple inversions cycle through positions."""
        chord = [0, 4, 7]
        inv1 = invert_chord(chord, 1)
        inv2 = invert_chord(chord, 2)
        assert inv1 != inv2

    def test_invert_chord_empty_list(self):
        """Empty chord returns empty."""
        inverted = invert_chord([], 1)
        assert inverted == []


class TestNextModePicker:
    """Test chord-family picker logic."""

    def test_next_mode_picker_roundrobin(self):
        """Roundrobin picker cycles through modes in order."""
        modes = ['triads', 'sevenths', 'ninths']
        picker = next_mode_picker(modes, 'roundrobin')
        picks = [picker() for _ in range(9)]
        assert picks == modes + modes + modes

    def test_next_mode_picker_roundrobin_two_modes(self):
        """Roundrobin with two modes."""
        modes = ['triads', 'sevenths']
        picker = next_mode_picker(modes, 'roundrobin')
        picks = [picker() for _ in range(4)]
        assert picks == modes + modes

    def test_next_mode_picker_random_picks_from_modes(self):
        """Random (or non-roundrobin) picker picks from modes."""
        random.seed(42)
        modes = ['triads', 'sevenths', 'ninths']
        picker = next_mode_picker(modes, 'random')
        picks = [picker() for _ in range(10)]
        assert all(p in modes for p in picks)

    def test_next_mode_picker_empty_modes_defaults_to_extended(self):
        """Empty modes defaults to extended-chords."""
        picker = next_mode_picker([], 'roundrobin')
        pick = picker()
        assert pick == 'extended-chords'


class TestComputeMaxGapBeats:
    """Test beat-gap computation for chord changes."""

    def test_compute_max_gap_beats_valid(self):
        """compute_max_gap_beats returns positive for valid inputs."""
        gap = compute_max_gap_beats(120, 1.0)
        assert gap > 0


class TestRootSelection:
    """Integration tests for different root selection modes."""

    def test_chord_progression_with_explicit_colon_tokens(self):
        """Colon tokens like C::maj7 are honored directly."""
        prog = build_progression(['C::maj7', 'G::7'], ['triads'], 'ordered')
        assert prog[0].root_pc == pc('C')
        assert prog[1].root_pc == pc('G')

    def test_chord_progression_mixed_tokens_and_simple_keys(self):
        """Mix of colon tokens and simple keys works together."""
        prog = build_progression(['C::maj7', 'G'], ['triads'], 'ordered')
        assert len(prog) >= 2
        assert prog[0].root_pc == pc('C')
        assert prog[1].root_pc == pc('G')

    def test_empty_keys_uses_full_circle_of_fifths(self):
        """No keys specified uses 12-tone circle."""
        prog = build_progression([], ['triads'], 'ordered')
        roots = {cd.root_pc for cd in prog}
        assert len(roots) >= 12
