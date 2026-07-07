"""End-to-end smoke tests: drive music_generator.main() for every render mode
and assert a valid, non-empty MIDI is produced. These guard the render paths
(which unit tests don't touch) so refactors can't break them silently.
"""

import glob
import shutil
import sys

import mido
import pytest

import music_generator as mg

OUT = mg.MIDI_DIR


def _run(argv):
    old = sys.argv
    sys.argv = ["music_generator.py", *argv]
    try:
        mg.main()
    finally:
        sys.argv = old


def _assert_valid_midi(slug, min_notes=1):
    files = sorted(glob.glob(str(OUT / slug / "*.mid")))
    assert files, f"no MIDI produced for {slug}"
    mid = mido.MidiFile(files[-1])
    notes = [m for tr in mid.tracks for m in tr
             if m.type == "note_on" and m.velocity > 0]
    assert len(notes) >= min_notes, f"{slug}: only {len(notes)} notes"
    assert mid.length > 0


@pytest.fixture
def slug(request):
    name = "_itest_" + request.node.name.replace("[", "_").replace("]", "")
    d = OUT / name
    if d.exists():
        shutil.rmtree(d)
    yield name
    if d.exists():
        shutil.rmtree(d)


def test_render_ostinato(slug):
    _run(["--mode", "ostinato", "--keys", "C::maj,F::maj,G::maj/C,A::min7",
          "--seconds", "4", "--seed", "1", "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_mixed(slug):
    _run(["--mode", "mixed", "--seconds", "4", "--seed", "1",
          "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_arpeggio_with_custom_bass(slug):
    _run(["--mode", "ostinato", "--keys", "C::maj9,A::min11",
          "--satb-style", "arpeggio", "--bass-style", "octaves",
          "--seconds", "4", "--seed", "1", "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_dense_voicing(slug):
    _run(["--mode", "ostinato", "--keys", "E::mystic,C::messiaen_resonance",
          "--voicing", "dense", "--seconds", "4", "--seed", "1",
          "--no-play", "--out", slug])
    _assert_valid_midi(slug, min_notes=8)  # dense = many simultaneous tones


def test_render_song(slug, tmp_path):
    song = tmp_path / "song.yml"
    song.write_text(
        "title: t\ntempo: 120\n"
        "defaults: {instrument: piano, chord_length: h}\n"
        "sections:\n"
        "  - {name: a, repeat: 1, keys: 'C::maj, F::maj'}\n"
        "  - {name: b, bars: 2, tempo: 90, keys: 'G::maj'}\n",
        encoding="utf-8")
    _run(["--song", str(song), "--out", slug])
    _assert_valid_midi(slug)


def test_render_song_no_perc_silences_drums(slug, tmp_path):
    # gap-analysis I1, song-path regression: --no-perc used to be ignored when
    # rendering a --song file, because the CLI's arr_overrides builder checked
    # `if args.perc_main:` instead of whether --perc-main/--no-perc was set.
    song = tmp_path / "song.yml"
    song.write_text(
        "title: t\ntempo: 120\n"
        "defaults: {instrument: piano, chord_length: h}\n"
        "sections:\n"
        "  - {name: a, repeat: 1, keys: 'C::maj, F::maj'}\n",
        encoding="utf-8")
    _run(["--song", str(song), "--no-perc", "--out", slug])
    files = sorted(glob.glob(str(OUT / slug / "*.mid")))
    assert files
    mid = mido.MidiFile(files[-1])
    drum_notes = [m for tr in mid.tracks for m in tr
                  if m.type == "note_on" and m.velocity > 0
                  and m.channel == mg.DRUM_CH]
    assert not drum_notes
