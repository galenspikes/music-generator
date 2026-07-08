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


# ---- soundfont discovery (Thread D v2: master-side "which soundfonts do I have") ----

def test_list_soundfonts_empty_when_dir_missing(tmp_path):
    assert render.list_soundfonts(tmp_path / "nope") == []


def test_list_soundfonts_finds_sf2_files_sorted(tmp_path):
    (tmp_path / "zeta.sf2").write_bytes(b"")
    (tmp_path / "alpha.sf2").write_bytes(b"")
    (tmp_path / "notes.txt").write_bytes(b"")  # ignored, not .sf2
    assert render.list_soundfonts(tmp_path) == ["alpha.sf2", "zeta.sf2"]


def test_resolve_sf2_passes_through_real_paths_and_none(tmp_path):
    real = tmp_path / "somewhere.sf2"
    real.write_bytes(b"")
    assert render.resolve_sf2(str(real)) == str(real)
    assert render.resolve_sf2(None) is None
    assert render.resolve_sf2("has/a/slash.sf2") == "has/a/slash.sf2"


def test_resolve_sf2_finds_bare_name_in_soundfonts_dir(tmp_path):
    (tmp_path / "arachno.sf2").write_bytes(b"")
    assert render.resolve_sf2("arachno", tmp_path) == str(tmp_path / "arachno.sf2")
    assert render.resolve_sf2("arachno.sf2", tmp_path) == str(tmp_path / "arachno.sf2")


def test_resolve_sf2_unresolved_name_passes_through(tmp_path):
    assert render.resolve_sf2("not-there", tmp_path) == "not-there"


def test_main_list_soundfonts_reports_none_found(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(render, "SOUNDFONTS_DIR", tmp_path / "empty")
    assert render.main(["--list-soundfonts"]) == 0
    assert "No .sf2 files found" in capsys.readouterr().out


def test_main_list_soundfonts_lists_files(tmp_path, monkeypatch, capsys):
    (tmp_path / "arachno.sf2").write_bytes(b"")
    monkeypatch.setattr(render, "SOUNDFONTS_DIR", tmp_path)
    assert render.main(["--list-soundfonts"]) == 0
    assert "arachno.sf2" in capsys.readouterr().out


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
        ["--keys", "C::maj,F::maj", "--seconds", "4",
         "--seed", "1", "--no-play", "--out", slug])
    assert midi.endswith(".mid")
    assert Path(midi).exists()
    assert glob.glob(str(mg.MIDI_DIR / slug / "*.mid"))


# ---- stem WAV bounce (Thread 4b follow-up) ----

def test_find_stem_midis_empty_without_stems(tmp_path):
    midi = tmp_path / "song.mid"
    midi.write_text("")
    assert render.find_stem_midis(str(midi)) == {}


def test_find_stem_midis_finds_siblings(tmp_path):
    midi = tmp_path / "song.mid"
    midi.write_text("")
    for name in ("soprano", "bass", "drums"):
        (tmp_path / f"song_{name}.mid").write_text("")
    found = render.find_stem_midis(str(midi))
    assert set(found) == {"soprano", "bass", "drums"}
    assert found["bass"] == str(tmp_path / "song_bass.mid")


def test_run_generator_with_stems_writes_sibling_midis(slug):
    midi = render.run_generator(
        ["--keys", "C::maj,F::maj", "--stems", "--seconds", "4",
         "--seed", "1", "--no-play", "--out", slug])
    found = render.find_stem_midis(midi)
    # flat renders have no lead voice; the other five stems must all exist
    assert set(found) == {"soprano", "alto", "tenor", "bass", "drums"}
    for path in found.values():
        assert Path(path).exists()


def test_build_parser_stems_flag_defaults_false():
    parser = render.build_parser(None, "audio")
    args = parser.parse_args([])
    assert args.stems is False


def test_build_parser_stems_flag_parses():
    parser = render.build_parser(None, "audio")
    args, _ = parser.parse_known_args(["--stems"])
    assert args.stems is True
