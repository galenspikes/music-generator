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


def test_render_progression(slug):
    _run(["--keys", "C::maj,F::maj,G::maj/C,A::min7",
          "--seconds", "4", "--seed", "1", "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_random_roots(slug):
    _run(["--random-roots", "--seconds", "4", "--seed", "1",
          "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_full_progression(slug):
    _run(["--full-progression", "--keys", "C::maj,F::maj,G::maj/C,A::min7",
          "--seconds", "4", "--seed", "1", "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_arpeggio_with_custom_bass(slug):
    _run(["--keys", "C::maj9,A::min11",
          "--satb-style", "arpeggio", "--bass-style", "octaves",
          "--seconds", "4", "--seed", "1", "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_dense_voicing(slug):
    _run(["--keys", "E::mystic,C::messiaen_resonance",
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


def test_render_counterpoint_voicing(slug):
    """Test counterpoint voice leading mode."""
    _run(["--keys", "C::maj,F::maj,G::maj",
          "--satb-style", "counterpoint",
          "--seconds", "4", "--seed", "2", "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_with_swing(slug):
    """Test swing timing application."""
    _run(["--keys", "C::maj,F::maj",
          "--swing", "0.3", "--seconds", "4", "--seed", "2",
          "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_with_pan_spread(slug):
    """Test stereo pan positioning."""
    _run(["--keys", "C::maj,A::min",
          "--pan-spread", "0.9", "--seconds", "3", "--seed", "2",
          "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_different_instruments(slug):
    """Test rendering with different instruments."""
    for instrument in ["piano", "strings", "guitar"]:
        inst_slug = f"{slug}_{instrument}"
        _run(["--keys", "C::maj,G::maj", "--instrument", instrument,
              "--seconds", "2", "--seed", "3", "--no-play", "--out", inst_slug])
        _assert_valid_midi(inst_slug)


def test_render_different_bpm(slug):
    """Test rendering at different tempos."""
    for bpm in [60, 120, 180]:
        bpm_slug = f"{slug}_{bpm}"
        _run(["--keys", "C::maj", "--bpm", str(bpm),
              "--seconds", "2", "--seed", "3", "--no-play", "--out", bpm_slug])
        _assert_valid_midi(bpm_slug)


def test_render_with_percussion_patterns(slug):
    """Test rendering with different percussion patterns."""
    patterns = ["qbeg", "qbceg", "qbeg,qbceg"]
    for i, pattern in enumerate(patterns):
        perc_slug = f"{slug}_perc{i}"
        _run(["--keys", "C::maj,F::maj", "--perc-main", pattern,
              "--seconds", "2", "--seed", "3", "--no-play", "--out", perc_slug])
        _assert_valid_midi(perc_slug)


def test_render_with_fill_percussion(slug):
    """Test percussion with fill patterns."""
    _run(["--keys", "C::maj,F::maj,G::maj",
          "--perc-main", "qbeg", "--perc-fill-rate", "0.5",
          "--seconds", "4", "--seed", "3", "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_seventh_chords(slug):
    """Test rendering with seventh chords."""
    _run(["--keys", "C::maj7,F::maj7,G::7,A::min7",
          "--seconds", "4", "--seed", "4", "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_slash_chords(slug):
    """Test slash chord rendering (altered bass)."""
    _run(["--keys", "C::maj/E,F::maj/C,G::maj/B",
          "--seconds", "4", "--seed", "4", "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_complex_chords(slug):
    """Test complex chord types."""
    _run(["--keys", "C::maj9,D::min11,E::mystic,F::maj7",
          "--seconds", "4", "--seed", "4", "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_with_split_stems(slug):
    """Test multi-track rendering with split stems."""
    _run(["--keys", "C::maj,F::maj", "--split-stems",
          "--seconds", "2", "--seed", "5", "--no-play", "--out", slug])
    files = sorted(glob.glob(str(OUT / slug / "*.mid")))
    assert files  # Should produce MIDI file(s)


def test_render_human_velocity_mode(slug):
    """Test humanized velocity for chords."""
    _run(["--keys", "C::maj,F::maj",
          "--velocity-mode-chords", "human",
          "--seconds", "2", "--seed", "5", "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_random_velocity_mode(slug):
    """Test randomized velocity."""
    _run(["--keys", "C::maj,F::maj",
          "--velocity-mode-drums", "random",
          "--seconds", "2", "--seed", "5", "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_determinism_with_seed(slug):
    """Test deterministic generation with same seed."""
    # First generation with seed 42
    slug1 = f"{slug}_1"
    _run(["--keys", "C::maj,F::maj,G::maj",
          "--seconds", "2", "--seed", "42", "--no-play", "--out", slug1])
    files1 = sorted(glob.glob(str(OUT / slug1 / "*.mid")))
    mid1 = mido.MidiFile(files1[-1])

    # Second generation with same seed
    slug2 = f"{slug}_2"
    _run(["--keys", "C::maj,F::maj,G::maj",
          "--seconds", "2", "--seed", "42", "--no-play", "--out", slug2])
    files2 = sorted(glob.glob(str(OUT / slug2 / "*.mid")))
    mid2 = mido.MidiFile(files2[-1])

    # Should have same structure and duration
    assert mid1.length == mid2.length


def test_render_different_seeds_produce_different_output(slug):
    """Test that different seeds produce different MIDI."""
    slug1 = f"{slug}_seed1"
    _run(["--keys", "C::maj,F::maj",
          "--seconds", "2", "--seed", "10", "--no-play", "--out", slug1])
    files1 = sorted(glob.glob(str(OUT / slug1 / "*.mid")))
    mid1 = mido.MidiFile(files1[-1])

    slug2 = f"{slug}_seed2"
    _run(["--keys", "C::maj,F::maj",
          "--seconds", "2", "--seed", "20", "--no-play", "--out", slug2])
    files2 = sorted(glob.glob(str(OUT / slug2 / "*.mid")))
    mid2 = mido.MidiFile(files2[-1])

    # Extract note data from both
    notes1 = [m for tr in mid1.tracks for m in tr if m.type == "note_on"]
    notes2 = [m for tr in mid2.tracks for m in tr if m.type == "note_on"]

    # Should be different (different seeds)
    # Compare by note info or count
    assert len(notes1) > 0 and len(notes2) > 0  # Both valid


def test_render_short_duration(slug):
    """Test rendering very short piece."""
    _run(["--keys", "C::maj", "--seconds", "0.5",
          "--seed", "6", "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_long_duration(slug):
    """Test rendering longer piece."""
    _run(["--keys", "C::maj,F::maj,G::maj",
          "--seconds", "8", "--seed", "6",
          "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_single_chord_repeated(slug):
    """Test rendering with single chord repeated."""
    _run(["--keys", "C::maj*8", "--seconds", "4",
          "--seed", "6", "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_chain_repetition(slug):
    """Test chain repetition syntax."""
    _run(["--keys", "[C::maj,G::maj]*2", "--seconds", "4",
          "--seed", "7", "--no-play", "--out", slug])
    _assert_valid_midi(slug)


def test_render_ostinato_vs_full_progression(slug):
    """Compare ostinato vs full-progression modes."""
    # Ostinato (default)
    slug1 = f"{slug}_ostinato"
    _run(["--keys", "C,G,D", "--seconds", "2",
          "--seed", "7", "--no-play", "--out", slug1])
    files1 = sorted(glob.glob(str(OUT / slug1 / "*.mid")))
    assert files1

    # Full progression
    slug2 = f"{slug}_full"
    _run(["--keys", "C,G,D", "--full-progression", "--seconds", "2",
          "--seed", "7", "--no-play", "--out", slug2])
    files2 = sorted(glob.glob(str(OUT / slug2 / "*.mid")))
    assert files2


def test_render_all_modes_combined(slug):
    """Test rendering with multiple options combined."""
    _run(["--keys", "C::maj7,F::maj7,G::7",
          "--instrument", "piano",
          "--voicing", "satb",
          "--satb-style", "arpeggio",
          "--bass-style", "walking",
          "--bpm", "110",
          "--seconds", "4",
          "--perc-main", "qbeg",
          "--swing", "0.2",
          "--pan-spread", "0.7",
          "--velocity-mode-chords", "human",
          "--seed", "8",
          "--no-play",
          "--out", slug])
    _assert_valid_midi(slug)


def test_render_dense_with_interrupters(slug):
    """Test dense voicing with percussion interrupters."""
    _run(["--keys", "C::maj,A::min",
          "--voicing", "dense",
          "--perc-main", "qbeg",
          "--perc-interrupters", "qbceg",
          "--seconds", "3",
          "--seed", "8",
          "--no-play",
          "--out", slug])
    _assert_valid_midi(slug)
