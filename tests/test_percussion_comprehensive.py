"""Comprehensive tests for percussion module.

Tests percussion parsing, drum map management, and interrupter pattern selection.
Covers the percussion token DSL: <duration><drums>[modifiers]
"""

import random

import pytest

import music_generator as M
from percussion import (
    PercHit,
    PercStage,
    PercPlan,
    parse_single_token,
    parse_pattern,
    choose_perc_pattern,
    build_perc_from_args,
    set_active_drum_map,
    get_drum_map,
)


class TestPercHitStructure:
    """Test PercHit data structure."""

    def test_perc_hit_creation(self):
        """PercHit can be created with note."""
        hit = PercHit(note=35)  # Kick drum
        assert hit.note == 35
        assert hit.vel_offset == 0
        assert hit.probability == 1.0
        assert hit.flam is None

    def test_perc_hit_with_modifiers(self):
        """PercHit supports velocity, probability, and flam."""
        hit = PercHit(note=38, vel_offset=10, probability=0.7, flam=0.125)
        assert hit.note == 38
        assert hit.vel_offset == 10
        assert hit.probability == pytest.approx(0.7)
        assert hit.flam == pytest.approx(0.125)


class TestPercStageStructure:
    """Test PercStage data structure."""

    def test_perc_stage_creation(self):
        """PercStage holds beats and a main pattern."""
        main_pattern = [(0.0, [PercHit(note=35)])]
        stage = PercStage(beats=4.0, main=main_pattern)
        assert stage.beats == 4.0
        assert len(stage.main) == 1

    def test_perc_stage_with_fills(self):
        """PercStage can have multiple fill patterns."""
        main = [(0.0, [PercHit(note=35)])]
        fill1 = [(0.0, [PercHit(note=38)])]
        fill2 = [(0.0, [PercHit(note=42)])]
        stage = PercStage(beats=4.0, main=main, fills=(fill1, fill2))
        assert stage.fills is not None
        assert len(stage.fills) == 2


class TestPercPlanStructure:
    """Test PercPlan data structure."""

    def test_perc_plan_creation(self):
        """PercPlan holds main pattern and optional stages/interrupters."""
        main = [(0.0, [PercHit(note=35)])]
        plan = PercPlan(main=main, interrupters=None, stages=None, fill_curve=None)
        assert len(plan.main) > 0
        assert plan.interrupters is None
        assert plan.stages is None


class TestParsePercussionTokens:
    """Test percussion token parsing."""

    def test_parse_single_token_simple_kick(self):
        """Parse simple kick token 'qb' (quarter note kick)."""
        beats, hits = parse_single_token('qb')
        assert beats == 1.0  # q = quarter = 1.0 beat
        assert len(hits) == 1
        assert hits[0].note == 36  # Bass drum

    def test_parse_single_token_multiple_drums(self):
        """Parse token with multiple drums 'qbg' (quarter: kick, closed hat)."""
        beats, hits = parse_single_token('qbg')
        assert beats == 1.0  # q = quarter = 1.0 beat
        assert len(hits) == 2

    def test_parse_single_token_rest(self):
        """Parse rest token 'qr' (quarter rest)."""
        beats, hits = parse_single_token('qr')
        assert beats == 1.0  # q = quarter = 1.0 beat
        assert len(hits) == 0

    def test_parse_single_token_with_velocity_modifier(self):
        """Parse drum with velocity modifier 'qb[vel=10]'."""
        beats, hits = parse_single_token('qb[vel=10]')
        assert beats == 1.0  # q = quarter = 1.0 beat
        assert len(hits) == 1
        assert hits[0].vel_offset == 10

    def test_parse_single_token_with_negative_velocity(self):
        """Parse drum with negative velocity 'qb[vel=-5]'."""
        beats, hits = parse_single_token('qb[vel=-5]')
        assert hits[0].vel_offset == -5

    def test_parse_single_token_with_probability(self):
        """Parse drum with probability 'qb[prob=0.7]'."""
        beats, hits = parse_single_token('qb[prob=0.7]')
        assert hits[0].probability == pytest.approx(0.7)

    def test_parse_single_token_with_flam(self):
        """Parse drum with flam modifier 'qb[flam=0.125]'."""
        beats, hits = parse_single_token('qb[flam=0.125]')
        assert hits[0].flam == pytest.approx(0.125)

    def test_parse_single_token_with_combined_modifiers(self):
        """Parse drum with all modifiers 'qb[vel=10,prob=0.8,flam=0.125]'."""
        beats, hits = parse_single_token('qb[vel=10,prob=0.8,flam=0.125]')
        assert hits[0].vel_offset == 10
        assert hits[0].probability == pytest.approx(0.8)
        assert hits[0].flam == pytest.approx(0.125)

    def test_parse_single_token_eighth_note(self):
        """Parse eighth note token 'eb' (eighth kick)."""
        beats, hits = parse_single_token('eb')
        assert beats == 0.5  # e = eighth = 0.5 beat
        assert len(hits) == 1

    def test_parse_single_token_half_note(self):
        """Parse half note token 'hb' (half kick)."""
        beats, hits = parse_single_token('hb')
        assert beats == 2.0  # h = half = 2.0 beats
        assert len(hits) == 1

    def test_parse_single_token_whole_note(self):
        """Parse whole note token 'wb' (whole kick)."""
        beats, hits = parse_single_token('wb')
        assert beats == 4.0  # w = whole = 4.0 beats
        assert len(hits) == 1

    def test_parse_single_token_invalid_duration_raises(self):
        """Invalid duration letter raises error."""
        with pytest.raises(ValueError, match="Bad duration"):
            parse_single_token('Xb')

    def test_parse_single_token_unknown_drum_raises(self):
        """Unknown drum letter raises error."""
        with pytest.raises(ValueError, match="Unknown drum letter"):
            parse_single_token('q1')  # '1' is not a valid drum letter


class TestDrumMapLoading:
    """Test drum map loading and access."""

    def test_get_drum_map_returns_dict(self):
        """get_drum_map returns a dictionary."""
        map_ = get_drum_map()
        assert isinstance(map_, dict)
        assert len(map_) > 0

    def test_drum_map_has_common_drums(self):
        """Drum map includes common drums."""
        map_ = get_drum_map()
        # Check for common drum abbreviations
        drums_needed = {'b', 'e', 'g', 'c'}  # kick, rimshot, closed hat, snare
        for drum in drums_needed:
            assert drum in map_, f"Missing drum '{drum}' in map"

    def test_drum_map_all_entries_valid(self):
        """All drum map entries are valid MIDI notes."""
        map_ = get_drum_map()
        for key, value in map_.items():
            assert isinstance(key, str) and len(key) == 1
            assert isinstance(value, int)
            assert 0 <= value <= 127  # Valid MIDI note range

    def test_set_active_drum_map_fallback(self):
        """set_active_drum_map with None uses fallback."""
        map_ = set_active_drum_map(None)
        assert isinstance(map_, dict)
        assert len(map_) > 0


class TestChoosePercPattern:
    """Test interrupter pattern selection."""

    def test_choose_perc_pattern_zero_fill_rate(self):
        """With fill_rate=0.0, always returns main pattern."""
        main = [(0.0, [PercHit(note=35)])]
        interrupters = [[(0.0, [PercHit(note=38)])]]
        for _ in range(10):
            result = choose_perc_pattern(main, interrupters, fill_rate=0.0)
            assert result == main

    def test_choose_perc_pattern_full_fill_rate(self):
        """With fill_rate=1.0, always returns an interrupter."""
        main = [(0.0, [PercHit(note=35)])]
        interrupter = [(0.0, [PercHit(note=38)])]
        interrupters = [interrupter]
        for _ in range(10):
            result = choose_perc_pattern(main, interrupters, fill_rate=1.0)
            assert result == interrupter

    def test_choose_perc_pattern_no_interrupters(self):
        """With no interrupters, always returns main."""
        main = [(0.0, [PercHit(note=35)])]
        result = choose_perc_pattern(main, None, fill_rate=0.5)
        assert result == main

    def test_choose_perc_pattern_respects_probability(self):
        """fill_rate parameter affects selection probability."""
        random.seed(42)
        main = [(0.0, [PercHit(note=35)])]
        interrupter = [(0.0, [PercHit(note=38)])]
        interrupters = [interrupter]

        selections = []
        for _ in range(100):
            result = choose_perc_pattern(main, interrupters, fill_rate=0.5)
            selections.append(result == interrupter)

        # Should be roughly 50% interrupters (with seed 42 and 100 trials)
        interrupter_count = sum(selections)
        assert 30 < interrupter_count < 70  # Allow for randomness


class TestBuildPercFromArgs:
    """Test percussion building from CLI arguments."""

    def test_build_perc_from_args_basic(self):
        """Basic perc-main argument builds percussion."""
        args = M.build_parser().parse_args([
            '--keys', 'C::maj7',
            '--perc-main', 'qbeg,qbceg',
            '--bpm', '120',
            '--seconds', '8',
        ])
        M.apply_arg_normalization(args)
        perc_plan = build_perc_from_args(args)
        assert isinstance(perc_plan, PercPlan)
        assert perc_plan.main is not None
        assert len(perc_plan.main) > 0

    def test_build_perc_from_args_with_modifiers(self):
        """Percussion modifiers in tokens are parsed."""
        args = M.build_parser().parse_args([
            '--keys', 'C::maj7',
            '--perc-main', 'qb[vel=10],qe[prob=0.8]g',
            '--bpm', '120',
            '--seconds', '4',
        ])
        M.apply_arg_normalization(args)
        perc_plan = build_perc_from_args(args)
        assert isinstance(perc_plan, PercPlan)

    def test_build_perc_from_args_no_perc(self):
        """No percussion argument is handled gracefully."""
        args = M.build_parser().parse_args([
            '--keys', 'C::maj7',
            '--bpm', '120',
            '--seconds', '4',
        ])
        M.apply_arg_normalization(args)
        perc_plan = build_perc_from_args(args)
        assert isinstance(perc_plan, PercPlan)


class TestPercussionIntegration:
    """Integration tests with the full render pipeline."""

    def test_perc_renders_without_error(self):
        """Percussion integrates with full render."""
        args = M.build_parser().parse_args([
            '--keys', 'C::maj7, G::7',
            '--perc-main', 'qbeg,qbceg',
            '--bpm', '120',
            '--seconds', '4',
            '--no-play',
        ])
        M.apply_arg_normalization(args)
        midi, meta = M.build_flat_midi(args)
        assert midi is not None
        # Should have percussion metadata
        assert 'perc_stages_declared' in meta

    def test_perc_with_fill_rate(self):
        """Percussion fill rate applies."""
        args = M.build_parser().parse_args([
            '--keys', 'C::maj7',
            '--perc-main', 'qbeg',
            '--perc-interrupters', 'qbceg',
            '--perc-fill-rate', '0.5',
            '--bpm', '120',
            '--seconds', '8',
            '--no-play',
        ])
        M.apply_arg_normalization(args)
        midi, meta = M.build_flat_midi(args)
        assert midi is not None

    def test_perc_humanization(self):
        """Percussion velocity humanization applies."""
        args = M.build_parser().parse_args([
            '--keys', 'C::maj7',
            '--perc-main', 'qbeg',
            '--velocity-mode-drums', 'human',
            '--bpm', '120',
            '--seconds', '4',
            '--no-play',
        ])
        M.apply_arg_normalization(args)
        midi, meta = M.build_flat_midi(args)
        assert midi is not None


class TestPercussionEdgeCases:
    """Test edge cases in percussion."""

    def test_single_drum_repeats(self):
        """Single drum in pattern repeats."""
        args = M.build_parser().parse_args([
            '--keys', 'C::maj7',
            '--perc-main', 'qb',
            '--bpm', '120',
            '--seconds', '4',
        ])
        M.apply_arg_normalization(args)
        perc_plan = build_perc_from_args(args)
        assert isinstance(perc_plan, PercPlan)

    def test_rest_only_pattern(self):
        """Pattern with only rests works."""
        args = M.build_parser().parse_args([
            '--keys', 'C::maj7',
            '--perc-main', 'qr',
            '--bpm', '120',
            '--seconds', '4',
        ])
        M.apply_arg_normalization(args)
        perc_plan = build_perc_from_args(args)
        assert isinstance(perc_plan, PercPlan)

    def test_zero_probability_hit(self):
        """Hit with prob=0.0 has valid structure."""
        beats, hits = parse_single_token('qb[prob=0.0]')
        assert len(hits) == 1
        assert hits[0].probability == pytest.approx(0.0)

    def test_full_probability_hit(self):
        """Hit with prob=1.0 always plays."""
        beats, hits = parse_single_token('qb[prob=1.0]')
        assert len(hits) == 1
        assert hits[0].probability == pytest.approx(1.0)

    def test_probability_clamped_to_range(self):
        """Probability outside [0,1] is clamped."""
        # Values outside 0-1 should be clamped
        beats, hits = parse_single_token('qb[prob=1.5]')
        assert hits[0].probability == pytest.approx(1.0)

    def test_multiple_drums_same_token(self):
        """Multiple drums in one token are parsed."""
        beats, hits = parse_single_token('qbegc')
        assert len(hits) == 4  # kick, open hat, closed hat, snare


class TestPercussionPatternParsing:
    """Test parsing complete percussion patterns."""

    def test_parse_pattern_splits_tokens(self):
        """parse_pattern splits comma-separated tokens."""
        # parse_pattern takes a string and optional drum_map
        result = parse_pattern('qbeg,qbceg', drum_map=None)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_parse_pattern_empty_string(self):
        """Empty pattern string is handled."""
        result = parse_pattern('', drum_map=None)
        assert isinstance(result, list)
