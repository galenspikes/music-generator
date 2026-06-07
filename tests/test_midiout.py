"""Tests for MidiOut program assignment, incl. per-voice instruments."""

import music_generator as M


def _program_changes_by_channel(midi):
    """Map channel -> last program_change value across all tracks."""
    out = {}
    for tr in midi.mid.tracks:
        for msg in tr:
            if msg.type == "program_change":
                out[msg.channel] = msg.program
    return out


def test_split_stems_creates_four_voice_channels():
    m = M.MidiOut(bpm=120, fname="x.mid", split_stems=True)
    # soprano/alto/tenor/bass -> channels 0..3
    assert m.chord_channels == {"soprano": 0, "alto": 1, "tenor": 2, "bass": 3}


def test_set_program_applies_to_all_voices():
    m = M.MidiOut(bpm=120, fname="x.mid", split_stems=True)
    m.set_program(4)  # epiano on every chord channel
    pc = _program_changes_by_channel(m)
    for ch in (0, 1, 2, 3):
        assert pc[ch] == 4
    assert pc[M.DRUM_CH] == 0  # drum channel untouched


def test_voice_instruments_override_only_named_voice():
    m = M.MidiOut(bpm=120, fname="x.mid", split_stems=True)
    bass = M.resolve_instrument("bass")  # GM 32
    m.set_voice_programs({"bass": bass}, default_program=4)
    pc = _program_changes_by_channel(m)
    assert pc[m.chord_channels["soprano"]] == 4
    assert pc[m.chord_channels["alto"]] == 4
    assert pc[m.chord_channels["tenor"]] == 4
    assert pc[m.chord_channels["bass"]] == bass  # only bass differs


def test_voice_instruments_multiple():
    m = M.MidiOut(bpm=120, fname="x.mid", split_stems=True)
    saw, strings, bass = (M.resolve_instrument(n)
                          for n in ("saw", "strings", "bass"))
    m.set_voice_programs({"soprano": saw, "bass": bass},
                         default_program=strings)
    pc = _program_changes_by_channel(m)
    assert pc[m.chord_channels["soprano"]] == saw
    assert pc[m.chord_channels["alto"]] == strings  # default
    assert pc[m.chord_channels["tenor"]] == strings  # default
    assert pc[m.chord_channels["bass"]] == bass


def test_ensemble_mode_single_channel_uses_default():
    m = M.MidiOut(bpm=120, fname="x.mid", split_stems=False)
    # per-voice map is ignored structurally (one channel); default applies
    m.set_voice_programs({"bass": 32}, default_program=4)
    pc = _program_changes_by_channel(m)
    assert pc[M.CHORD_CH] == 4
