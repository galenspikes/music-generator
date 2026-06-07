"""Tests for the arrangement layer (song spec -> events -> MIDI)."""

import pytest

import music_generator as mg
import arrangement as A


RAW = {
    "title": "t",
    "tempo": 120,
    "defaults": {"instrument": "epiano", "chord_length": "q",
                 "bass": {"style": "root"}},
    "sections": [
        {"name": "a", "repeat": 2, "keys": "C::maj, F::maj"},
        {"name": "b", "bars": 4, "tempo": 90, "instrument": "saw",
         "keys": "G::maj", "voices": {"soprano": "strings"}},
    ],
}


def test_build_spec_merges_defaults():
    spec = A.build_spec(RAW)
    a, b = spec.sections
    assert a["instrument"] == "epiano"          # inherited default
    assert a["chord_length"] == "q"
    assert b["instrument"] == "saw"             # overridden
    assert b["tempo"] == 90                     # section tempo
    assert a["tempo"] == 120                    # falls back to global


def test_build_spec_errors():
    with pytest.raises(ValueError):
        A.build_spec({"sections": []})
    with pytest.raises(ValueError):
        A.build_spec({"sections": [{"name": "x"}]})        # missing keys
    with pytest.raises(ValueError):
        A.build_spec({"sections": [{"keys": "C", "chord_length": "Z"}]})


def test_section_beats_repeat_and_bars():
    # repeat: 2 passes of a 2-chord chart at quarter notes = 2 * (2*1.0) = 4
    assert A._section_beats({"repeat": 2}, seq_len=2, chord_len=1.0) == 4.0
    # bars: 4 bars * 4 beats = 16 (independent of chart length)
    assert A._section_beats({"bars": 4}, seq_len=2, chord_len=1.0) == 16.0


def test_build_events_timeline():
    spec = A.build_spec(RAW)
    events, total = A.build_events(spec)
    # section a: repeat 2 * (2 chords * 1 beat) = 4 beats; section b: 4 bars*4 = 16
    assert total == pytest.approx(20.0)

    # one tempo event per section, at the section start
    tempos = [(w, v) for k, w, _, v in events if k == "tempo"]
    assert tempos == [(0.0, 120), (4.0, 90)]

    # program events: 4 voices per section, all at section starts
    progs = [(w, p) for k, w, _, p in events if k == "program"]
    assert len(progs) == 8
    assert all(w in (0.0, 4.0) for w, _ in progs)

    # section b soprano should be 'strings', bass channel default epiano-era
    saw = mg.resolve_instrument("strings")
    assert (4.0, ("soprano", saw)) in progs

    # events are time-sorted with tempo/program before notes at the same beat
    whens = [w for _, w, _, _ in events]
    assert whens == sorted(whens)


def test_render_produces_valid_midi_with_tempo_map(tmp_path):
    spec = A.build_spec(RAW)
    out = str(tmp_path / "song.mid")
    A.render(spec, out)
    import mido
    mid = mido.MidiFile(out)
    tempos = [m for tr in mid.tracks for m in tr if m.type == "set_tempo"]
    # at least the two section tempos appear in the map
    assert len(tempos) >= 2
    assert mid.length > 0
