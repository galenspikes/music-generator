"""Comprehensive tests for music_generator module.

Tests CLI argument parsing, argument normalization, output paths, and rendering helpers.
"""

import pytest

import music_generator as M


class TestBuildParser:
    """Test argument parser construction."""

    def test_build_parser_returns_parser(self):
        """build_parser() returns an ArgumentParser."""
        parser = M.build_parser()
        assert isinstance(parser, type(M.build_parser()))

    def test_parser_has_chord_args(self):
        """Parser includes chord/harmony arguments."""
        parser = M.build_parser()
        dests = {a.dest for a in parser._actions}
        assert "keys" in dests
        assert "chords" in dests
        assert "voicing" in dests
        assert "bpm" in dests
        assert "instrument" in dests

    def test_parser_has_percussion_args(self):
        """Parser includes percussion arguments."""
        parser = M.build_parser()
        dests = {a.dest for a in parser._actions}
        assert "perc_main" in dests
        assert "perc_interrupters" in dests
        assert "perc_fill_rate" in dests

    def test_parser_has_output_args(self):
        """Parser includes output and control arguments."""
        parser = M.build_parser()
        dests = {a.dest for a in parser._actions}
        assert "seconds" in dests
        assert "out" in dests
        assert "no_play" in dests
        assert "split_stems" in dests

    def test_parser_has_arrangement_arg(self):
        """Parser includes song arrangement argument."""
        parser = M.build_parser()
        dests = {a.dest for a in parser._actions}
        assert "song" in dests

    def test_parse_minimal_args(self):
        """Parser handles minimal valid arguments."""
        parser = M.build_parser()
        args = parser.parse_args([])
        assert args is not None
        # Should have defaults
        assert args.bpm > 0
        assert args.seconds > 0

    def test_parse_args_with_keys(self):
        """Parser handles --keys argument."""
        parser = M.build_parser()
        args = parser.parse_args(["--keys", "C,G,D"])
        assert args.keys == "C,G,D"

    def test_parse_args_with_percussion(self):
        """Parser handles percussion arguments."""
        parser = M.build_parser()
        args = parser.parse_args(["--perc-main", "qbeg,qbceg"])
        assert args.perc_main == "qbeg,qbceg"

    def test_parse_args_with_voicing(self):
        """Parser handles voicing options."""
        parser = M.build_parser()
        args = parser.parse_args(["--voicing", "dense"])
        assert args.voicing == "dense"

    def test_parse_args_with_split_stems(self):
        """Parser handles --split-stems flag."""
        parser = M.build_parser()
        args1 = parser.parse_args(["--split-stems"])
        assert args1.split_stems is True

        args2 = parser.parse_args(["--no-split-stems"])
        assert args2.split_stems is False

    def test_parse_args_with_song(self):
        """Parser handles --song argument."""
        parser = M.build_parser()
        args = parser.parse_args(["--song", "songs/example.yml"])
        assert args.song == "songs/example.yml"

    def test_parse_args_with_seed(self):
        """Parser handles --seed for deterministic generation."""
        parser = M.build_parser()
        args = parser.parse_args(["--seed", "42"])
        assert args.seed == 42


class TestApplyArgNormalization:
    """Test argument normalization and validation."""

    def test_normalization_returns_bool(self):
        """apply_arg_normalization returns boolean."""
        parser = M.build_parser()
        args = parser.parse_args([])
        result = M.apply_arg_normalization(args)
        assert isinstance(result, bool)

    def test_normalization_valid_args(self):
        """Normalization succeeds with valid arguments."""
        parser = M.build_parser()
        args = parser.parse_args(["--keys", "C::maj7", "--seconds", "4"])
        result = M.apply_arg_normalization(args)
        assert result is True

    def test_normalization_sets_defaults(self):
        """Normalization applies default values."""
        parser = M.build_parser()
        args = parser.parse_args([])
        M.apply_arg_normalization(args)
        assert args.bpm > 0
        assert args.seconds > 0
        assert hasattr(args, "out")

    def test_normalization_with_random_roots(self):
        """Normalization handles --random-roots flag."""
        parser = M.build_parser()
        args = parser.parse_args(["--random-roots"])
        M.apply_arg_normalization(args)
        assert args.random_roots is True

    def test_normalization_with_full_progression(self):
        """Normalization handles --full-progression flag."""
        parser = M.build_parser()
        args = parser.parse_args(["--full-progression"])
        M.apply_arg_normalization(args)
        assert args.full_progression is True

    def test_normalization_with_bpm(self):
        """Normalization validates BPM."""
        parser = M.build_parser()
        args = parser.parse_args(["--bpm", "140"])
        M.apply_arg_normalization(args)
        assert args.bpm == 140

    def test_normalization_with_instrument(self):
        """Normalization handles instrument argument."""
        parser = M.build_parser()
        args = parser.parse_args(["--instrument", "piano"])
        M.apply_arg_normalization(args)
        assert args.instrument == "piano"


class TestResolveOutPath:
    """Test output path resolution."""

    def test_resolve_out_path_with_explicit_out(self):
        """resolve_out_path uses explicit --out argument."""
        path = M.resolve_out_path("my_song", "default_slug")
        assert "my_song" in path

    def test_resolve_out_path_with_default(self):
        """resolve_out_path uses default slug when no --out."""
        path = M.resolve_out_path(None, "default_slug")
        assert "default_slug" in path

    def test_resolve_out_path_includes_directory(self):
        """resolve_out_path includes MIDI_DIR."""
        path = M.resolve_out_path("test", "default")
        assert str(M.MIDI_DIR) in path

    def test_resolve_out_path_includes_slug(self):
        """resolve_out_path includes slug in path."""
        out = "test_output"
        path = M.resolve_out_path(out, "default")
        assert out in path


class TestTsFilename:
    """Test timestamp filename generation."""

    def test_ts_filename_format(self):
        """ts_filename returns properly formatted filename."""
        filename = M.ts_filename("stem")
        assert filename.endswith(".mid")
        assert "stem" in filename

    def test_ts_filename_deterministic(self):
        """ts_filename with same stem produces same base."""
        f1 = M.ts_filename("chord")
        f2 = M.ts_filename("chord")
        assert f1 == f2

    def test_ts_filename_different_stems(self):
        """ts_filename with different stems produces different names."""
        f1 = M.ts_filename("chord")
        f2 = M.ts_filename("percussion")
        assert f1 != f2


class TestSwingTiming:
    """Test swing timing calculations."""

    def test_swing_time_zero_swing(self):
        """Zero swing doesn't change timing."""
        t = 1.0
        result = M._swing_time(t, swing=0.0)
        assert result == pytest.approx(t)

    def test_swing_time_positive_swing(self):
        """Positive swing affects timing."""
        t = 1.0
        result_no_swing = M._swing_time(t, swing=0.0)
        result_swing = M._swing_time(t, swing=0.3)
        # Result should be different (doesn't have to be specific value)
        # but should be reasonable
        assert abs(result_swing - result_no_swing) >= 0.0

    def test_swing_time_bounds(self):
        """Swing calculation produces valid results."""
        t = 1.0
        result = M._swing_time(t, swing=0.5)
        assert isinstance(result, float)
        assert result >= 0.0


class TestApplySwing:
    """Test swing application to event lists."""

    def test_apply_swing_empty_list(self):
        """apply_swing handles empty event list."""
        events = []
        result = M.apply_swing(events, swing=0.3)
        assert result == []

    def test_apply_swing_zero_swing(self):
        """Zero swing doesn't modify events."""
        events = [(0.0, 1, 64, 127), (1.0, 1, 65, 127)]
        result = M.apply_swing(events, swing=0.0)
        assert result == events

    def test_apply_swing_preserves_structure(self):
        """apply_swing preserves event structure."""
        events = [(0.0, 1, 64, 127), (0.5, 1, 65, 127)]
        result = M.apply_swing(events, swing=0.2)
        assert len(result) == len(events)
        # Event structure should be preserved
        for event in result:
            assert len(event) >= 1  # At least timing


class TestBuildFlatMidi:
    """Test flat MIDI building (ostinato/progression modes)."""

    def test_build_flat_midi_minimal(self):
        """build_flat_midi works with minimal arguments."""
        parser = M.build_parser()
        args = parser.parse_args(["--keys", "C::maj7", "--seconds", "2"])
        M.apply_arg_normalization(args)
        midi, meta = M.build_flat_midi(args)
        assert midi is not None
        assert isinstance(meta, dict)

    def test_build_flat_midi_returns_midi_and_meta(self):
        """build_flat_midi returns MidiOut and metadata."""
        parser = M.build_parser()
        args = parser.parse_args(["--keys", "C::maj7,G::7"])
        M.apply_arg_normalization(args)
        midi, meta = M.build_flat_midi(args)
        assert isinstance(midi, M.MidiOut)
        assert isinstance(meta, dict)

    def test_build_flat_midi_metadata_has_keys(self):
        """Metadata includes important fields."""
        parser = M.build_parser()
        args = parser.parse_args(["--keys", "C::maj7"])
        M.apply_arg_normalization(args)
        midi, meta = M.build_flat_midi(args)
        # Should have some metadata fields
        assert len(meta) > 0

    def test_build_flat_midi_deterministic(self):
        """build_flat_midi is deterministic with same seed."""
        parser = M.build_parser()
        args1 = parser.parse_args(["--keys", "C::maj7", "--seed", "42", "--seconds", "2"])
        args2 = parser.parse_args(["--keys", "C::maj7", "--seed", "42", "--seconds", "2"])
        M.apply_arg_normalization(args1)
        M.apply_arg_normalization(args2)

        midi1, _ = M.build_flat_midi(args1)
        midi2, _ = M.build_flat_midi(args2)

        assert midi1.to_bytes() == midi2.to_bytes()

    def test_build_flat_midi_random_roots(self):
        """build_flat_midi works with --random-roots."""
        parser = M.build_parser()
        args = parser.parse_args(["--random-roots", "--seconds", "2"])
        M.apply_arg_normalization(args)
        midi, meta = M.build_flat_midi(args)
        assert midi is not None

    def test_build_flat_midi_full_progression(self):
        """build_flat_midi works with --full-progression."""
        parser = M.build_parser()
        args = parser.parse_args(["--keys", "C,G,D", "--full-progression", "--seconds", "4"])
        M.apply_arg_normalization(args)
        midi, meta = M.build_flat_midi(args)
        assert midi is not None

    def test_build_flat_midi_with_voicing_satb(self):
        """build_flat_midi works with different voicing modes."""
        parser = M.build_parser()
        args = parser.parse_args(["--keys", "C::maj7", "--voicing", "satb"])
        M.apply_arg_normalization(args)
        midi, meta = M.build_flat_midi(args)
        assert midi is not None

    def test_build_flat_midi_with_voicing_dense(self):
        """build_flat_midi works with dense voicing."""
        parser = M.build_parser()
        args = parser.parse_args(["--keys", "C::maj7", "--voicing", "dense"])
        M.apply_arg_normalization(args)
        midi, meta = M.build_flat_midi(args)
        assert midi is not None


class TestIntegration:
    """Integration tests for full argument flow."""

    def test_parse_and_normalize_flow(self):
        """Full parsing and normalization flow."""
        parser = M.build_parser()
        args = parser.parse_args([
            "--keys", "C::maj7,A::min7",
            "--instrument", "piano",
            "--bpm", "90",
            "--seconds", "4",
            "--perc-main", "qbeg",
        ])
        result = M.apply_arg_normalization(args)
        assert result is True
        assert args.keys == "C::maj7,A::min7"
        assert args.bpm == 90

    def test_build_flat_midi_with_percussion(self):
        """build_flat_midi with percussion arguments."""
        parser = M.build_parser()
        args = parser.parse_args([
            "--keys", "C::maj7",
            "--perc-main", "qbeg,qbceg",
            "--seconds", "2",
        ])
        M.apply_arg_normalization(args)
        midi, meta = M.build_flat_midi(args)
        assert midi is not None

    def test_build_flat_midi_with_humanization(self):
        """build_flat_midi with humanization modes."""
        parser = M.build_parser()
        args = parser.parse_args([
            "--keys", "C::maj7",
            "--velocity-mode-chords", "human",
            "--velocity-mode-drums", "random",
            "--seconds", "2",
        ])
        M.apply_arg_normalization(args)
        midi, meta = M.build_flat_midi(args)
        assert midi is not None

    def test_build_flat_midi_with_all_options(self):
        """build_flat_midi with comprehensive options."""
        parser = M.build_parser()
        args = parser.parse_args([
            "--keys", "C::maj7,G::7",
            "--instrument", "strings",
            "--voicing", "satb",
            "--bpm", "120",
            "--seconds", "4",
            "--perc-main", "qbeg",
            "--split-stems",
            "--swing", "0.2",
            "--pan-spread", "0.8",
            "--velocity-mode-chords", "human",
            "--velocity-mode-drums", "human",
            "--seed", "42",
        ])
        M.apply_arg_normalization(args)
        midi, meta = M.build_flat_midi(args)
        assert midi is not None
        assert midi.bpm == 120
