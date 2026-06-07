"""Tests for the render wrapper (render.py): pure helpers + generator glue."""

import glob
import shutil
from pathlib import Path

import pytest

import render
import music_generator as mg


# ---- pure helpers ----

def test_fx_opts_presets():
    assert render.fx_opts("none", True) == []
    assert "synth.reverb.active=1" in render.fx_opts("lush", True)
    assert "synth.chorus.active=1" in render.fx_opts("chorus-super", True)
    assert render.fx_opts("dry", True) == [
        "-o", "synth.chorus.active=0", "-o", "synth.reverb.active=0"]


def test_fx_opts_empty_without_sf2():
    assert render.fx_opts("lush", False) == []


def test_fx_opts_unknown_preset_errors():
    with pytest.raises(SystemExit):
        render.fx_opts("bogus", True)


def test_command_builders():
    assert render.fluidsynth_render_cmd("fs", ["-o", "x"], "a.wav", "s.sf2",
                                        "m.mid") == [
        "fs", "-q", "-ni", "-o", "x", "-F", "a.wav", "s.sf2", "m.mid"]
    ln = render.ffmpeg_loudnorm_cmd("ff", "i.wav", "o.wav")
    assert ln[:3] == ["ff", "-y", "-hide_banner"] and ln[-3:] == ["-ar", "44100", "o.wav"]
    assert render.ffmpeg_volume_cmd("ff", "i.wav", "o.wav", "2") == [
        "ff", "-y", "-hide_banner", "-loglevel", "error", "-i", "i.wav",
        "-af", "volume=2dB", "o.wav"]


def test_config_output_dir_parsing():
    cfg = {"default_wrapper_flags": [["--output-dir", "output/audio"]]}
    assert render._config_output_dir(cfg) == "output/audio"
    assert render._config_output_dir({}) is None


def test_find_tool_missing_returns_none():
    assert render.find_tool("definitely-not-a-real-tool-xyz") is None


# ---- generator glue (integration; no audio tools needed) ----

@pytest.fixture
def slug(request):
    name = "_rtest_" + request.node.name
    d = mg.MIDI_DIR / name
    if d.exists():
        shutil.rmtree(d)
    yield name
    if d.exists():
        shutil.rmtree(d)


def test_run_generator_returns_midi_path(slug):
    midi = render.run_generator(
        ["--mode", "ostinato", "--keys", "C::maj,F::maj", "--seconds", "4",
         "--seed", "1", "--no-play", "--out", slug])
    assert midi.endswith(".mid")
    assert Path(midi).exists()
    assert glob.glob(str(mg.MIDI_DIR / slug / "*.mid"))
