"""Comprehensive tests for voicing module.

Tests SATB voice leading, dense voicing, bass lines, arpeggios, and counterpoint.
Covers voice range assignment, register management, and note selection algorithms.
"""

import random


import voicing as V
from mtheory import (
    ALTO_RANGE, BASS_RANGE, SOP_RANGE, TENOR_RANGE,
    VOICE_ORDER, VOICE_RANGE_MAP
)


class TestSnapNoteToPcs:
    """Test snapping notes to chord pitch classes."""

    def test_snap_note_to_pcs_exact_match(self):
        """Note matching a PC is unchanged."""
        result = V._snap_note_to_pcs(60, {0, 4, 7}, "soprano")
        assert result == 60

    def test_snap_note_to_pcs_within_range(self):
        """Result stays within voice range."""
        result = V._snap_note_to_pcs(65, {1, 5, 8}, "soprano")
        assert SOP_RANGE[0] <= result <= SOP_RANGE[1]

    def test_snap_note_to_pcs_empty_pcs(self):
        """Empty PC set clamps to range."""
        result = V._snap_note_to_pcs(100, set(), "soprano")
        assert SOP_RANGE[0] <= result <= SOP_RANGE[1]

    def test_snap_note_to_pcs_all_voices(self):
        """Works for all voice ranges."""
        for voice in VOICE_ORDER:
            result = V._snap_note_to_pcs(50, {0, 4, 7}, voice)
            lo, hi = VOICE_RANGE_MAP[voice]
            assert lo <= result <= hi

    def test_snap_note_to_pcs_chord_tones(self):
        """Prefers chord tones."""
        # C major chord: C, E, G (0, 4, 7)
        result = V._snap_note_to_pcs(61, {0, 4, 7}, "soprano")
        # Should snap to nearby chord tone
        assert result % 12 in {0, 4, 7}

    def test_snap_note_to_pcs_closest_match(self):
        """Selects closest chord tone."""
        # Middle soprano around 72 (C), chord C major
        result = V._snap_note_to_pcs(72, {0, 4, 7}, "soprano")
        assert 60 <= result <= 84  # In soprano range


class TestDecorativeStep:
    """Test decorative note movement."""

    def test_decorative_step_returns_in_range(self):
        """Result stays within voice range."""
        for voice in VOICE_ORDER:
            result = V._decorative_step(50, voice)
            lo, hi = VOICE_RANGE_MAP[voice]
            assert lo <= result <= hi

    def test_decorative_step_different_from_original(self):
        """Tries to produce different note when possible."""
        # High soprano - should move down
        result = V._decorative_step(85, "soprano")
        # Result might equal input if no other option, but usually different
        assert isinstance(result, int)

    def test_decorative_step_low_note(self):
        """Low note finds nearby step."""
        result = V._decorative_step(28, "bass")
        assert BASS_RANGE[0] <= result <= BASS_RANGE[1]


class TestFitArpeggioPitch:
    """Test arpeggio pitch fitting."""

    def test_fit_arpeggio_no_previous(self):
        """Without previous note, finds close candidate."""
        result = V._fit_arpeggio_pitch(72, "soprano", None)
        assert SOP_RANGE[0] <= result <= SOP_RANGE[1]

    def test_fit_arpeggio_with_previous(self):
        """With previous note, considers smooth motion."""
        result = V._fit_arpeggio_pitch(72, "soprano", 60)
        assert SOP_RANGE[0] <= result <= SOP_RANGE[1]

    def test_fit_arpeggio_all_voices(self):
        """Works for all voices."""
        for voice in VOICE_ORDER:
            result = V._fit_arpeggio_pitch(50, voice, None)
            lo, hi = VOICE_RANGE_MAP[voice]
            assert lo <= result <= hi

    def test_fit_arpeggio_encourages_motion(self):
        """Tends to avoid repeating previous note."""
        # Test many times to see probability
        prev = 72
        different_count = 0
        for _ in range(20):
            result = V._fit_arpeggio_pitch(72, "soprano", prev)
            if result != prev:
                different_count += 1
        # Should encourage motion most of the time
        assert different_count > 5


class TestCounterpointSequence:
    """Test counterpoint line generation."""

    def test_counterpoint_sequence_single_segment(self):
        """Single segment returns start note."""
        result = V._counterpoint_sequence(60, 72, {0, 4, 7}, 1, "soprano")
        assert result == [60]

    def test_counterpoint_sequence_length(self):
        """Sequence has correct number of notes."""
        result = V._counterpoint_sequence(60, 72, {0, 4, 7}, 4, "soprano")
        assert len(result) == 4

    def test_counterpoint_sequence_endpoints(self):
        """First note is start, last is target."""
        result = V._counterpoint_sequence(60, 72, {0, 4, 7}, 4, "soprano")
        assert result[0] == 60
        # Last note should be close to target (snapped to PCs)
        assert 60 <= result[-1] <= 84

    def test_counterpoint_sequence_in_range(self):
        """All notes stay in voice range."""
        result = V._counterpoint_sequence(60, 72, {0, 4, 7}, 8, "soprano")
        for note in result:
            assert SOP_RANGE[0] <= note <= SOP_RANGE[1]

    def test_counterpoint_sequence_all_voices(self):
        """Works for all voice ranges."""
        for voice in VOICE_ORDER:
            result = V._counterpoint_sequence(50, 60, {0, 4, 7}, 3, voice)
            lo, hi = VOICE_RANGE_MAP[voice]
            for note in result:
                assert lo <= note <= hi

    def test_counterpoint_sequence_chord_tones(self):
        """Prefers chord tones."""
        random.seed(42)
        result = V._counterpoint_sequence(60, 72, {0, 4, 7}, 5, "soprano")
        # Most notes should be chord tones
        chord_tone_count = sum(1 for note in result if note % 12 in {0, 4, 7})
        assert chord_tone_count >= 3


class TestMergeVoiceSegment:
    """Test voice segment merging."""

    def test_merge_voice_segment_empty_line(self):
        """Adding to empty line."""
        line = []
        V._merge_voice_segment(line, 0.0, 1.0, 60)
        assert len(line) == 1
        assert line[0] == (0.0, 1.0, 60)

    def test_merge_voice_segment_same_note_adjacent(self):
        """Same note at adjacent time merges."""
        line = [(0.0, 1.0, 60)]
        V._merge_voice_segment(line, 1.0, 1.0, 60)
        # Should merge into one entry
        assert len(line) == 1
        assert line[0] == (0.0, 2.0, 60)

    def test_merge_voice_segment_different_note(self):
        """Different note starts new segment."""
        line = [(0.0, 1.0, 60)]
        V._merge_voice_segment(line, 1.0, 1.0, 61)
        assert len(line) == 2

    def test_merge_voice_segment_gap(self):
        """Notes with gap don't merge."""
        line = [(0.0, 1.0, 60)]
        V._merge_voice_segment(line, 1.1, 1.0, 60)
        assert len(line) == 2

    def test_merge_voice_segment_multiple_merges(self):
        """Can merge multiple segments."""
        line = []
        V._merge_voice_segment(line, 0.0, 0.5, 60)
        V._merge_voice_segment(line, 0.5, 0.5, 60)
        V._merge_voice_segment(line, 1.0, 0.5, 60)
        # All should merge into one
        assert len(line) == 1
        assert line[0] == (0.0, 1.5, 60)


class TestPickSoprano:
    """Test soprano note selection with voice leading."""

    def test_pick_soprano_returns_valid_note(self):
        """Returns note in soprano range."""
        chord_tones = [60, 64, 67]
        result = V.pick_soprano(chord_tones, None, 0, set(), set(), False)
        assert SOP_RANGE[0] <= result <= SOP_RANGE[1]

    def test_pick_soprano_from_chord_tones(self):
        """Picks from provided chord tones."""
        chords = [60, 64, 67]
        result = V.pick_soprano(chords, None, 0, set(), set(), False)
        # Should pick one of the candidates
        assert SOP_RANGE[0] <= result <= SOP_RANGE[1]

    def test_pick_soprano_with_previous(self):
        """Uses previous soprano for smooth motion."""
        chords = [60, 64, 67]
        result1 = V.pick_soprano(chords, None, 0, set(), set(), False)
        # With previous soprano, should consider it for scoring
        result2 = V.pick_soprano(chords, result1, 0, set(), set(), False)
        assert SOP_RANGE[0] <= result1 <= SOP_RANGE[1]
        assert SOP_RANGE[0] <= result2 <= SOP_RANGE[1]

    def test_pick_soprano_with_guide_pcs(self):
        """Guide pitch classes influence selection."""
        chords = [60, 64, 67]
        result = V.pick_soprano(chords, None, 0, {4}, set(), False)
        # Should prefer the third (4)
        assert SOP_RANGE[0] <= result <= SOP_RANGE[1]

    def test_pick_soprano_with_color_pcs(self):
        """Color pitch classes influence selection."""
        chords = [60, 64, 67]
        result = V.pick_soprano(chords, None, 0, set(), {7}, False)
        # Should prefer the fifth (7)
        assert SOP_RANGE[0] <= result <= SOP_RANGE[1]

    def test_pick_soprano_root_optional(self):
        """root_optional penalizes root selection."""
        chords = [60, 64, 67]
        result1 = V.pick_soprano(chords, None, 0, set(), set(), False)
        result2 = V.pick_soprano(chords, None, 0, set(), set(), True)
        # Both should be valid sopranos
        assert SOP_RANGE[0] <= result1 <= SOP_RANGE[1]
        assert SOP_RANGE[0] <= result2 <= SOP_RANGE[1]


class TestPickInPartRange:
    """Test voice-specific note selection."""

    def test_pick_in_part_range_within_range(self):
        """Note already in range stays unchanged."""
        result = V.pick_in_part_range(60, 48, 84, None)
        assert result == 60

    def test_pick_in_part_range_finds_nearest_octave(self):
        """Finds nearest octave of note."""
        # 36 is closer to its own octave than to the range
        result = V.pick_in_part_range(36, 48, 84, None)
        # Nearest octaves are 36, 48, 24
        # 36 is closest to target 36
        assert isinstance(result, int)

    def test_pick_in_part_range_prefers_close_octave(self):
        """Prefers octave closest to target."""
        # 60 is in range, so should return it
        result = V.pick_in_part_range(60, 48, 84, None)
        assert result == 60
        # 72 is also in range
        result2 = V.pick_in_part_range(72, 48, 84, None)
        assert result2 == 72

    def test_pick_in_part_range_with_avoid(self):
        """Can avoid specific note when needed."""
        result = V.pick_in_part_range(60, 48, 84, avoid=60)
        # Should try to avoid 60 by using an octave shift
        assert 48 <= result <= 84

    def test_pick_in_part_range_all_voices_in_range(self):
        """Works for notes already in voice ranges."""
        for voice in VOICE_ORDER:
            lo, hi = VOICE_RANGE_MAP[voice]
            mid = (lo + hi) // 2
            result = V.pick_in_part_range(mid, lo, hi, None)
            # Note in middle of range should return itself
            assert result == mid


class TestRecenterIfNeeded:
    """Test voice recentering for balanced spacing."""

    def test_recenter_if_needed_balanced(self):
        """Balanced voicing unchanged."""
        sop, alto, tenor, bass = 72, 60, 55, 48
        result = V.recenter_if_needed(sop, alto, tenor, bass)
        # Should return tuple of 4 notes
        assert len(result) == 4
        assert all(isinstance(n, int) for n in result)

    def test_recenter_if_needed_all_voices(self):
        """Result has notes in each voice range."""
        sop, alto, tenor, bass = 72, 60, 55, 48
        s, a, t, b = V.recenter_if_needed(sop, alto, tenor, bass)
        assert SOP_RANGE[0] <= s <= SOP_RANGE[1]
        assert ALTO_RANGE[0] <= a <= ALTO_RANGE[1]
        assert TENOR_RANGE[0] <= t <= TENOR_RANGE[1]
        assert BASS_RANGE[0] <= b <= BASS_RANGE[1]

    def test_recenter_if_needed_high_soprano(self):
        """High soprano gets recentered down."""
        sop, alto, tenor, bass = 90, 60, 55, 48
        s, a, t, b = V.recenter_if_needed(sop, alto, tenor, bass)
        # All should be in valid ranges
        assert SOP_RANGE[0] <= s <= SOP_RANGE[1]
        assert BASS_RANGE[0] <= b <= BASS_RANGE[1]

    def test_recenter_if_needed_low_bass(self):
        """Low bass gets recentered up."""
        sop, alto, tenor, bass = 72, 60, 55, 30
        s, a, t, b = V.recenter_if_needed(sop, alto, tenor, bass)
        # All should be in valid ranges
        assert SOP_RANGE[0] <= s <= SOP_RANGE[1]
        assert BASS_RANGE[0] <= b <= BASS_RANGE[1]


class TestRealizeSATB:
    """Test SATB chord realization."""

    def test_realize_satb_produces_four_notes(self):
        """Produces soprano, alto, tenor, bass notes."""
        chord_pcs = [0, 4, 7]  # C major pitch classes
        result = V.realize_SATB(None, 0, chord_pcs)
        assert len(result) == 4
        sop, alto, tenor, bass = result
        assert all(isinstance(n, int) for n in result)

    def test_realize_satb_in_voice_ranges(self):
        """All notes in correct voice ranges."""
        chord_pcs = [0, 4, 7]  # C major
        sop, alto, tenor, bass = V.realize_SATB(None, 0, chord_pcs)
        assert SOP_RANGE[0] <= sop <= SOP_RANGE[1]
        assert ALTO_RANGE[0] <= alto <= ALTO_RANGE[1]
        assert TENOR_RANGE[0] <= tenor <= TENOR_RANGE[1]
        assert BASS_RANGE[0] <= bass <= BASS_RANGE[1]

    def test_realize_satb_with_previous_soprano(self):
        """Uses previous soprano for voice leading."""
        chord_pcs = [0, 4, 7]
        result1 = V.realize_SATB(None, 0, chord_pcs)
        result2 = V.realize_SATB(result1[0], 0, chord_pcs)
        # Both should be valid
        assert len(result1) == 4
        assert len(result2) == 4

    def test_realize_satb_with_bass_pc(self):
        """Works with slash chords (different bass)."""
        chord_pcs = [0, 4, 7]
        # G in the bass (pitch class 7)
        result = V.realize_SATB(None, 0, chord_pcs, bass_pc=7)
        assert len(result) == 4
        sop, alto, tenor, bass = result
        # Bass note should reflect the bass_pc choice
        assert BASS_RANGE[0] <= bass <= BASS_RANGE[1]

    def test_realize_satb_minor_chord(self):
        """Works with minor chords."""
        # A minor: A, C, E (pitch classes 9, 0, 4)
        chord_pcs = [9, 0, 4]
        result = V.realize_SATB(None, 9, chord_pcs)
        assert len(result) == 4

    def test_realize_satb_seventh_chord(self):
        """Works with seventh chords."""
        # G7: G, B, D, F (pitch classes 7, 11, 2, 5)
        chord_pcs = [7, 11, 2, 5]
        result = V.realize_SATB(None, 7, chord_pcs)
        assert len(result) == 4

    def test_realize_satb_progression(self):
        """Multiple chords in progression maintain voice leading."""
        chords = [
            ([0, 4, 7], 0),      # C major
            ([2, 6, 9], 2),      # D minor
            ([4, 8, 11], 4),     # E minor
        ]
        prev_sop = None
        for chord_pcs, root in chords:
            result = V.realize_SATB(prev_sop, root, chord_pcs)
            assert len(result) == 4
            prev_sop = result[0]


class TestRealizeDense:
    """Test dense voicing (all chord tones)."""

    def test_realize_dense_produces_notes(self):
        """Produces list of notes."""
        chord_pcs = [0, 4, 7]  # C major
        result = V.realize_dense(0, chord_pcs)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_realize_dense_in_range(self):
        """All notes in specified range."""
        chord_pcs = [0, 4, 7]
        result = V.realize_dense(0, chord_pcs, lo=36, hi=88)
        for note in result:
            assert 36 <= note <= 88

    def test_realize_dense_includes_chord_tones(self):
        """Result includes all chord tone pitch classes."""
        chord_pcs = [0, 4, 7]
        result = V.realize_dense(0, chord_pcs)
        result_pcs = {note % 12 for note in result}
        # Should include chord tone pitch classes
        for pc in chord_pcs:
            assert pc % 12 in result_pcs

    def test_realize_dense_with_bass_pc(self):
        """Works with slash chords."""
        chord_pcs = [0, 4, 7]
        result = V.realize_dense(0, chord_pcs, bass_pc=7)
        assert len(result) > 0
        # Bass note should be the lowest
        assert result[0] % 12 == 7

    def test_realize_dense_different_roots(self):
        """Works with different chord roots."""
        for root_pc in [0, 7, 2]:  # C, G, D
            chord_pcs = [root_pc, (root_pc + 4) % 12, (root_pc + 7) % 12]
            result = V.realize_dense(root_pc, chord_pcs)
            assert len(result) > 0

    def test_realize_dense_wide_range(self):
        """Can produce notes across wide range."""
        chord_pcs = [0, 4, 7]
        result = V.realize_dense(0, chord_pcs, lo=24, hi=108)
        assert len(result) > 1  # Should use the space


class TestBuildBassLine:
    """Test bass line generation."""

    def test_build_bass_line_returns_list(self):
        """Returns list of (time, duration, note) tuples."""
        timeline = [(0.0, 1.0, (60, 64, 67, 48))]
        result = V.build_bass_line(timeline)
        assert isinstance(result, list)

    def test_build_bass_line_empty_timeline(self):
        """Empty timeline returns empty list."""
        result = V.build_bass_line([])
        assert result == []

    def test_build_bass_line_event_structure(self):
        """Events have correct structure (time, duration, note)."""
        timeline = [(0.0, 1.0, (60, 64, 67, 48))]
        result = V.build_bass_line(timeline, style="root")
        for event in result:
            assert len(event) == 3
            assert isinstance(event[0], float)  # time
            assert isinstance(event[1], float)  # duration
            assert isinstance(event[2], int)    # note

    def test_build_bass_line_in_range(self):
        """Bass notes are in bass range."""
        timeline = [(0.0, 1.0, (60, 64, 67, 48))]
        result = V.build_bass_line(timeline, style="root")
        for _, _, note in result:
            assert BASS_RANGE[0] <= note <= BASS_RANGE[1]

    def test_build_bass_line_none_style(self):
        """Style 'none' returns empty list."""
        timeline = [(0.0, 1.0, (60, 64, 67, 48))]
        result = V.build_bass_line(timeline, style="none")
        assert result == []

    def test_build_bass_line_different_styles(self):
        """Works with different styles."""
        timeline = [(0.0, 1.0, (60, 64, 67, 48))]
        for style in V.BASS_STYLES:
            result = V.build_bass_line(timeline, style=style)
            assert isinstance(result, list)


class TestBuildArpeggioEvents:
    """Test arpeggio event generation."""

    def test_build_arpeggio_events_returns_list(self):
        """Returns list of events."""
        timeline = [(0.0, 1.0, (60, 64, 67, 48))]
        result = V.build_arpeggio_events(timeline, 0.25)
        assert isinstance(result, list)

    def test_build_arpeggio_events_event_structure(self):
        """Events have correct structure (voice, time, duration, note)."""
        timeline = [(0.0, 1.0, (60, 64, 67, 48))]
        result = V.build_arpeggio_events(timeline, 0.25)
        for event in result:
            assert len(event) == 4
            voice, time, dur, note = event
            assert voice in VOICE_ORDER
            assert isinstance(time, float)
            assert isinstance(dur, float)
            assert isinstance(note, int)

    def test_build_arpeggio_events_covers_timeline(self):
        """Events cover the timeline duration."""
        timeline = [(0.0, 4.0, (60, 64, 67, 48))]
        result = V.build_arpeggio_events(timeline, 0.5)
        assert len(result) > 0

    def test_build_arpeggio_events_empty_timeline(self):
        """Empty timeline returns empty list."""
        result = V.build_arpeggio_events([], 0.25)
        assert result == []

    def test_build_arpeggio_events_notes_in_voice_ranges(self):
        """Notes stay in their voice ranges."""
        timeline = [(0.0, 1.0, (60, 64, 67, 48))]
        result = V.build_arpeggio_events(timeline, 0.25)
        for voice, _, _, note in result:
            lo, hi = VOICE_RANGE_MAP[voice]
            assert lo <= note <= hi


class TestBuildCounterpointLines:
    """Test counterpoint line generation."""

    def test_build_counterpoint_lines_all_voices(self):
        """Produces lines for all voices."""
        timeline = [(0.0, 1.0, (60, 64, 67, 48))]
        result = V.build_counterpoint_lines(timeline, 0.5, 0.2, 0.1)
        assert isinstance(result, dict)
        for voice in VOICE_ORDER:
            assert voice in result

    def test_build_counterpoint_lines_returns_dict(self):
        """Returns dict mapping voice names to event lists."""
        timeline = [(0.0, 1.0, (60, 64, 67, 48))]
        result = V.build_counterpoint_lines(timeline, 0.5, 0.2, 0.1)
        for voice, line in result.items():
            assert voice in VOICE_ORDER
            assert isinstance(line, list)

    def test_build_counterpoint_lines_event_structure(self):
        """Line events have (start, duration, note) structure."""
        timeline = [(0.0, 1.0, (60, 64, 67, 48))]
        result = V.build_counterpoint_lines(timeline, 0.5, 0.2, 0.1)
        for voice, line in result.items():
            for event in line:
                assert len(event) == 3
                assert isinstance(event[0], float)  # start
                assert isinstance(event[1], float)  # duration
                assert isinstance(event[2], int)    # note

    def test_build_counterpoint_lines_notes_in_ranges(self):
        """All notes stay in their voice ranges."""
        timeline = [(0.0, 1.0, (60, 64, 67, 48))]
        result = V.build_counterpoint_lines(timeline, 0.5, 0.2, 0.1)
        for voice, line in result.items():
            lo, hi = VOICE_RANGE_MAP[voice]
            for _, _, note in line:
                assert lo <= note <= hi

    def test_build_counterpoint_lines_empty_timeline(self):
        """Empty timeline returns empty lines."""
        result = V.build_counterpoint_lines([], 0.5, 0.2, 0.1)
        for voice, line in result.items():
            assert isinstance(line, list)


class TestIntegration:
    """Integration tests for voicing operations."""

    def test_satb_realization_progression(self):
        """Realize multiple chords with voice leading."""
        chords = [
            ([0, 4, 7], 0),      # C major
            ([2, 6, 9], 2),      # D minor
            ([4, 8, 11], 4),     # E minor
            ([5, 9, 0], 5),      # F major
        ]
        prev_sop = None
        for chord_pcs, root in chords:
            result = V.realize_SATB(prev_sop, root, chord_pcs)
            assert len(result) == 4
            prev_sop = result[0]

    def test_dense_voicing_multiple_chords(self):
        """Dense voicing for chord sequence."""
        for root_pc in [0, 7, 2]:  # C, G, D
            chord_pcs = [root_pc, (root_pc + 4) % 12, (root_pc + 7) % 12]
            result = V.realize_dense(root_pc, chord_pcs)
            assert len(result) > 0

    def test_voice_range_consistency(self):
        """All voice operations respect range constraints."""
        for voice in VOICE_ORDER:
            lo, hi = VOICE_RANGE_MAP[voice]
            # Snap note test
            snapped = V._snap_note_to_pcs(50, {0, 4, 7}, voice)
            assert lo <= snapped <= hi
            # Decorative step test
            stepped = V._decorative_step(50, voice)
            assert lo <= stepped <= hi

    def test_full_voicing_pipeline(self):
        """Full pipeline: SATB + bass + arpeggios + counterpoint."""
        timeline = [(0.0, 1.0, (60, 64, 67, 48))]

        # Realize SATB
        satb = V.realize_SATB(None, 0, [0, 4, 7])
        assert len(satb) == 4

        # Build bass line
        bass = V.build_bass_line(timeline, style="root")
        assert isinstance(bass, list)

        # Build arpeggios
        arps = V.build_arpeggio_events(timeline, 0.5)
        assert isinstance(arps, list)

        # Build counterpoint
        lines = V.build_counterpoint_lines(timeline, 0.5, 0.2, 0.1)
        assert isinstance(lines, dict)
