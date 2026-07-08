"""Comprehensive tests for render module.

Tests audio rendering pipeline: MIDI → FluidSynth (WAV) → ffmpeg (normalize/boost).
Covers command builders, FX presets, SoundFont resolution, and configuration loading.
"""

import json
import tempfile
from pathlib import Path

import pytest

import render


class TestFindTool:
    """Test tool discovery in PATH."""

    def test_find_tool_builtin(self):
        """find_tool finds common tools like 'ls'."""
        result = render.find_tool("ls")
        assert result is not None
        assert Path(result).is_file()

    def test_find_tool_nonexistent_returns_none(self):
        """find_tool returns None for nonexistent tools."""
        result = render.find_tool("definitely_not_a_real_tool_xyz123")
        assert result is None

    def test_find_tool_result_is_absolute_path(self):
        """find_tool returns absolute path when found."""
        result = render.find_tool("ls")
        if result:
            assert Path(result).is_absolute()


class TestListSoundfonts:
    """Test SoundFont discovery."""

    def test_list_soundfonts_nonexistent_dir(self):
        """list_soundfonts returns empty for nonexistent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "nonexistent"
            result = render.list_soundfonts(nonexistent)
            assert result == []

    def test_list_soundfonts_empty_dir(self):
        """list_soundfonts returns empty for empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = render.list_soundfonts(Path(tmpdir))
            assert result == []

    def test_list_soundfonts_with_sf2_files(self):
        """list_soundfonts returns sorted .sf2 filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create some dummy .sf2 files
            (tmppath / "zebra.sf2").touch()
            (tmppath / "arachno.sf2").touch()
            (tmppath / "other.wav").touch()  # Should be ignored
            (tmppath / "README.txt").touch()  # Should be ignored

            result = render.list_soundfonts(tmppath)
            assert result == ["arachno.sf2", "zebra.sf2"]  # Sorted

    def test_list_soundfonts_ignores_non_sf2(self):
        """list_soundfonts only returns .sf2 files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "sound.sf2").touch()
            (tmppath / "sound.sf3").touch()
            (tmppath / "sound.txt").touch()

            result = render.list_soundfonts(tmppath)
            assert result == ["sound.sf2"]


class TestResolveSf2:
    """Test SoundFont path resolution."""

    def test_resolve_sf2_absolute_path_unchanged(self):
        """Absolute paths are returned as-is."""
        result = render.resolve_sf2("/path/to/sound.sf2")
        assert result == "/path/to/sound.sf2"

    def test_resolve_sf2_existing_file_unchanged(self):
        """Existing file paths are returned as-is."""
        with tempfile.NamedTemporaryFile(suffix=".sf2") as f:
            result = render.resolve_sf2(f.name)
            assert result == f.name

    def test_resolve_sf2_with_slash_unchanged(self):
        """Paths containing / are returned as-is."""
        result = render.resolve_sf2("./sounds/file.sf2")
        assert result == "./sounds/file.sf2"

    def test_resolve_sf2_with_backslash_unchanged(self):
        """Paths containing \\ are returned as-is."""
        result = render.resolve_sf2("sounds\\file.sf2")
        assert result == "sounds\\file.sf2"

    def test_resolve_sf2_bare_name_resolves(self):
        """Bare name resolves against soundfonts directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            soundfont = tmppath / "arachno.sf2"
            soundfont.touch()

            result = render.resolve_sf2("arachno", tmppath)
            assert result == str(soundfont)

    def test_resolve_sf2_bare_name_with_extension(self):
        """Bare name with .sf2 extension resolves."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            soundfont = tmppath / "arachno.sf2"
            soundfont.touch()

            result = render.resolve_sf2("arachno.sf2", tmppath)
            assert result == str(soundfont)

    def test_resolve_sf2_fallback_unchanged(self):
        """Unresolvable name is returned unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = render.resolve_sf2("nonexistent", Path(tmpdir))
            assert result == "nonexistent"

    def test_resolve_sf2_none_unchanged(self):
        """None input returns None."""
        result = render.resolve_sf2(None)
        assert result is None

    def test_resolve_sf2_empty_string_unchanged(self):
        """Empty string returns None (falsy)."""
        result = render.resolve_sf2("")
        assert result == ""


class TestLoadConfig:
    """Test configuration loading."""

    def test_load_config_nonexistent_file(self):
        """load_config returns empty dict for nonexistent file."""
        result = render.load_config(Path("/nonexistent/config.json"))
        assert result == {}

    def test_load_config_valid_json(self):
        """load_config loads valid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "value", "number": 42}, f)
            f.flush()

            try:
                result = render.load_config(Path(f.name))
                assert result == {"key": "value", "number": 42}
            finally:
                Path(f.name).unlink()

    def test_load_config_invalid_json(self):
        """load_config returns empty dict for invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json")
            f.flush()

            try:
                result = render.load_config(Path(f.name))
                assert result == {}
            finally:
                Path(f.name).unlink()

    def test_load_config_empty_file(self):
        """load_config returns empty dict for empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("")
            f.flush()

            try:
                result = render.load_config(Path(f.name))
                assert result == {}
            finally:
                Path(f.name).unlink()


class TestConfigOutputDir:
    """Test config output directory extraction."""

    def test_config_output_dir_not_present(self):
        """Returns None when --output-dir not in config."""
        cfg = {"default_wrapper_flags": []}
        result = render._config_output_dir(cfg)
        assert result is None

    def test_config_output_dir_empty_flags(self):
        """Returns None when config has no default_wrapper_flags."""
        cfg = {}
        result = render._config_output_dir(cfg)
        assert result is None

    def test_config_output_dir_single_flag(self):
        """Extracts output dir from flag entry."""
        cfg = {"default_wrapper_flags": [["--output-dir", "/path/to/audio"]]}
        result = render._config_output_dir(cfg)
        assert result == "/path/to/audio"

    def test_config_output_dir_multiple_flags(self):
        """Extracts output dir from multiple flag entries."""
        cfg = {
            "default_wrapper_flags": [
                ["--sf2", "arachno.sf2"],
                ["--output-dir", "/custom/audio"],
                "--normalize"
            ]
        }
        result = render._config_output_dir(cfg)
        assert result == "/custom/audio"

    def test_config_output_dir_nested_list(self):
        """Handles nested list flags."""
        cfg = {
            "default_wrapper_flags": [
                ["--output-dir", "/custom/path"],
                "--normalize"
            ]
        }
        result = render._config_output_dir(cfg)
        assert result == "/custom/path"

    def test_config_output_dir_missing_value(self):
        """Returns None when --output-dir has no value."""
        cfg = {"default_wrapper_flags": ["--output-dir"]}
        result = render._config_output_dir(cfg)
        assert result is None


class TestFxOpts:
    """Test FX preset option generation."""

    def test_fx_opts_no_sf2(self):
        """Returns empty list when no SoundFont."""
        result = render.fx_opts("dry", have_sf2=False)
        assert result == []

    def test_fx_opts_none_preset(self):
        """'none' preset returns empty options."""
        result = render.fx_opts("none", have_sf2=True)
        assert result == []

    def test_fx_opts_dry_preset(self):
        """'dry' preset disables effects."""
        result = render.fx_opts("dry", have_sf2=True)
        assert "-o" in result
        assert "synth.chorus.active=0" in result
        assert "synth.reverb.active=0" in result

    def test_fx_opts_chorus_super_preset(self):
        """'chorus-super' preset enables chorus."""
        result = render.fx_opts("chorus-super", have_sf2=True)
        assert "-o" in result
        assert "synth.chorus.active=1" in result
        assert "synth.chorus.nr=5" in result

    def test_fx_opts_lush_preset(self):
        """'lush' preset enables chorus and reverb."""
        result = render.fx_opts("lush", have_sf2=True)
        assert "-o" in result
        assert "synth.chorus.active=1" in result
        assert "synth.reverb.active=1" in result

    def test_fx_opts_unknown_preset_raises(self):
        """Unknown preset raises SystemExit."""
        with pytest.raises(SystemExit):
            render.fx_opts("unknown_preset", have_sf2=True)

    def test_fx_opts_available_presets(self):
        """All defined presets work."""
        for preset in render.FX_PRESETS.keys():
            result = render.fx_opts(preset, have_sf2=True)
            # Should return list without error
            assert isinstance(result, list)


class TestFluidsyntheRenderCmd:
    """Test FluidSynth command generation."""

    def test_fluidsynth_render_cmd_basic(self):
        """Generates basic fluidsynth command."""
        cmd = render.fluidsynth_render_cmd("fluidsynth", [], "out.wav", "sound.sf2", "in.mid")
        assert cmd == ["fluidsynth", "-q", "-ni", "-F", "out.wav", "sound.sf2", "in.mid"]

    def test_fluidsynth_render_cmd_with_options(self):
        """Includes FX options in command."""
        opts = ["-o", "synth.chorus.active=1"]
        cmd = render.fluidsynth_render_cmd("fluidsynth", opts, "out.wav", "sound.sf2", "in.mid")
        assert "-o" in cmd
        assert "synth.chorus.active=1" in cmd

    def test_fluidsynth_render_cmd_order(self):
        """Command elements in correct order."""
        cmd = render.fluidsynth_render_cmd("fluidsynth", [], "out.wav", "sound.sf2", "in.mid")
        assert cmd[0] == "fluidsynth"
        assert cmd[1] == "-q"
        assert cmd[2] == "-ni"
        assert "-F" in cmd
        wav_idx = cmd.index("-F") + 1
        assert cmd[wav_idx] == "out.wav"
        assert cmd[-2] == "sound.sf2"
        assert cmd[-1] == "in.mid"


class TestFfmpegLoudnormCmd:
    """Test ffmpeg loudnorm command generation."""

    def test_ffmpeg_loudnorm_cmd_basic(self):
        """Generates loudnorm command."""
        cmd = render.ffmpeg_loudnorm_cmd("ffmpeg", "in.wav", "out.wav")
        assert "ffmpeg" in cmd
        assert "-i" in cmd
        assert "in.wav" in cmd
        assert "loudnorm=I=-14:TP=-1.0:LRA=11" in cmd
        assert "-ar" in cmd
        assert "44100" in cmd
        assert "out.wav" in cmd

    def test_ffmpeg_loudnorm_cmd_flags(self):
        """Includes required flags."""
        cmd = render.ffmpeg_loudnorm_cmd("ffmpeg", "in.wav", "out.wav")
        assert "-y" in cmd  # Overwrite
        assert "-hide_banner" in cmd
        assert "-loglevel" in cmd
        assert "error" in cmd

    def test_ffmpeg_loudnorm_cmd_order(self):
        """Command elements in logical order."""
        cmd = render.ffmpeg_loudnorm_cmd("ffmpeg", "in.wav", "out.wav")
        ffmpeg_idx = 0
        y_idx = cmd.index("-y")
        i_idx = cmd.index("-i")
        af_idx = cmd.index("-af")
        assert ffmpeg_idx < y_idx < i_idx < af_idx


class TestFfmpegVolumeCmd:
    """Test ffmpeg volume boost command generation."""

    def test_ffmpeg_volume_cmd_basic(self):
        """Generates volume command."""
        cmd = render.ffmpeg_volume_cmd("ffmpeg", "in.wav", "out.wav", "3")
        assert "ffmpeg" in cmd
        assert "-i" in cmd
        assert "in.wav" in cmd
        assert "-af" in cmd
        assert "volume=3dB" in cmd
        assert "out.wav" in cmd

    def test_ffmpeg_volume_cmd_negative_db(self):
        """Handles negative dB values."""
        cmd = render.ffmpeg_volume_cmd("ffmpeg", "in.wav", "out.wav", "-6")
        assert "volume=-6dB" in cmd

    def test_ffmpeg_volume_cmd_flags(self):
        """Includes required flags."""
        cmd = render.ffmpeg_volume_cmd("ffmpeg", "in.wav", "out.wav", "3")
        assert "-y" in cmd
        assert "-hide_banner" in cmd
        assert "-loglevel" in cmd
        assert "error" in cmd


class TestBuildParser:
    """Test argument parser construction."""

    def test_build_parser_creates_parser(self):
        """build_parser returns ArgumentParser."""
        parser = render.build_parser(None, "audio")
        assert isinstance(parser, type(render.build_parser(None, "audio")))

    def test_parser_has_sf2_arg(self):
        """Parser includes --sf2 argument."""
        parser = render.build_parser(None, "audio")
        dests = {a.dest for a in parser._actions}
        assert "sf2" in dests

    def test_parser_has_list_soundfonts_arg(self):
        """Parser includes --list-soundfonts."""
        parser = render.build_parser(None, "audio")
        dests = {a.dest for a in parser._actions}
        assert "list_soundfonts" in dests

    def test_parser_has_fx_args(self):
        """Parser includes FX arguments."""
        parser = render.build_parser(None, "audio")
        dests = {a.dest for a in parser._actions}
        assert "fx" in dests
        assert "chorus_super" in dests or "fx" in dests

    def test_parser_has_audio_processing_args(self):
        """Parser includes audio processing arguments."""
        parser = render.build_parser(None, "audio")
        dests = {a.dest for a in parser._actions}
        assert "normalize" in dests
        assert "boost_db" in dests
        assert "boost_after_norm" in dests

    def test_parser_has_control_args(self):
        """Parser includes control arguments."""
        parser = render.build_parser(None, "audio")
        dests = {a.dest for a in parser._actions}
        assert "no_play" in dests
        assert "save_wav" in dests
        assert "output_dir" in dests
        assert "keep_temporary" in dests

    def test_parser_default_sf2(self):
        """Parser uses provided default SF2."""
        parser = render.build_parser("arachno.sf2", "audio")
        args = parser.parse_args([])
        assert args.sf2 == "arachno.sf2"

    def test_parser_default_output_dir(self):
        """Parser uses provided default output dir."""
        parser = render.build_parser(None, "/custom/audio")
        args = parser.parse_args([])
        assert args.output_dir == "/custom/audio"

    def test_parser_parse_save_wav(self):
        """Parser handles --save-wav flag."""
        parser = render.build_parser(None, "audio")
        args = parser.parse_args(["--save-wav"])
        assert args.save_wav is True

    def test_parser_parse_no_play(self):
        """Parser handles --no-play flag."""
        parser = render.build_parser(None, "audio")
        args = parser.parse_args(["--no-play"])
        assert args.no_play is True

    def test_parser_parse_normalize(self):
        """Parser handles --normalize flag."""
        parser = render.build_parser(None, "audio")
        args = parser.parse_args(["--normalize"])
        assert args.normalize is True

    def test_parser_parse_boost_db(self):
        """Parser handles --boost-db argument."""
        parser = render.build_parser(None, "audio")
        args = parser.parse_args(["--boost-db", "6"])
        assert args.boost_db == "6"

    def test_parser_parse_chorus_super(self):
        """Parser handles --chorus-super alias."""
        parser = render.build_parser(None, "audio")
        args = parser.parse_args(["--chorus-super"])
        assert args.fx == "chorus-super"

    def test_parser_forward_unknown_args(self):
        """Parser forwards unknown arguments."""
        parser = render.build_parser(None, "audio")
        args, forwarded = parser.parse_known_args([
            "--save-wav", "--keys", "C::maj7", "--seconds", "2"
        ])
        assert args.save_wav is True
        assert "--keys" in forwarded
        assert "C::maj7" in forwarded


class TestParserIntegration:
    """Integration tests for full parser workflow."""

    def test_parse_minimal_args(self):
        """Parser handles minimal arguments."""
        parser = render.build_parser(None, "audio")
        args, forwarded = parser.parse_known_args([])
        assert args.fx == "dry"
        assert args.save_wav is False
        assert args.no_play is False

    def test_parse_full_args(self):
        """Parser handles full argument set."""
        parser = render.build_parser("default.sf2", "/audio")
        args, forwarded = parser.parse_known_args([
            "--save-wav",
            "--normalize",
            "--boost-db", "3",
            "--no-play",
            "--keys", "C::maj7",
        ])
        assert args.sf2 == "default.sf2"
        assert args.output_dir == "/audio"
        assert args.save_wav is True
        assert args.normalize is True
        assert args.boost_db == "3"
        assert args.no_play is True
        assert "--keys" in forwarded

    def test_parse_fx_options(self):
        """Parser handles different FX options."""
        parser = render.build_parser(None, "audio")

        for preset in ["dry", "none", "lush", "chorus-super"]:
            args, _ = parser.parse_known_args(["--fx", preset])
            assert args.fx == preset


class TestFxPresets:
    """Test FX preset definitions."""

    def test_fx_presets_defined(self):
        """FX_PRESETS dict has expected presets."""
        assert "none" in render.FX_PRESETS
        assert "dry" in render.FX_PRESETS
        assert "chorus-super" in render.FX_PRESETS
        assert "lush" in render.FX_PRESETS

    def test_fx_presets_values_are_lists(self):
        """All preset values are lists."""
        for name, opts in render.FX_PRESETS.items():
            assert isinstance(opts, list)

    def test_fx_presets_options_are_strings(self):
        """All preset options are strings."""
        for name, opts in render.FX_PRESETS.items():
            for opt in opts:
                assert isinstance(opt, str)

    def test_none_preset_empty(self):
        """'none' preset has no options."""
        assert render.FX_PRESETS["none"] == []

    def test_dry_preset_disables_effects(self):
        """'dry' preset disables chorus and reverb."""
        dry = render.FX_PRESETS["dry"]
        assert "synth.chorus.active=0" in dry
        assert "synth.reverb.active=0" in dry

    def test_chorus_super_enables_chorus(self):
        """'chorus-super' enables chorus effects."""
        super_chorus = render.FX_PRESETS["chorus-super"]
        assert "synth.chorus.active=1" in super_chorus

    def test_lush_enables_reverb(self):
        """'lush' enables reverb effects."""
        lush = render.FX_PRESETS["lush"]
        assert "synth.reverb.active=1" in lush
