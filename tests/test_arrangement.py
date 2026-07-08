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


def test_render_with_stems_writes_stem_files(tmp_path):
    spec = A.build_spec(RAW)
    out = str(tmp_path / "song.mid")
    A.render(spec, out, stems=True)
    for name in ("soprano", "alto", "tenor", "bass", "drums"):
        assert (tmp_path / f"song_{name}.mid").exists()


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


# --- Thread 1a: form references (blocks + form) --------------------------

FORM_RAW = {
    "title": "form-song",
    "tempo": 120,
    "defaults": {"chord_length": "q"},
    "blocks": {
        "verse": {"keys": "C::maj, F::maj", "bass": {"style": "root"}},
        "chorus": {"keys": "G::maj, C::maj", "bass": {"style": "octaves"}},
    },
    "form": ["verse", "chorus", "verse", {"chorus": {"tempo": 130}}],
}


def test_expand_form_names_and_overrides():
    spec = A.build_spec(FORM_RAW)
    names = [s["name"] for s in spec.sections]
    assert names == ["verse", "chorus", "verse-2", "chorus-2"]
    assert spec.sections[0]["bass"]["style"] == "root"
    assert spec.sections[1]["bass"]["style"] == "octaves"
    # inline per-occurrence override applies only to that one instance
    assert spec.sections[3]["tempo"] == 130
    assert spec.sections[1]["tempo"] == 120


def test_expand_form_unknown_block_errors():
    bad = {"blocks": {"verse": {"keys": "C"}}, "form": ["chorus"]}
    with pytest.raises(ValueError):
        A.build_spec(bad)


def test_expand_form_requires_blocks():
    with pytest.raises(ValueError):
        A.build_spec({"form": ["verse"]})


def test_expand_form_bad_entry_errors():
    bad = {"blocks": {"verse": {"keys": "C"}},
           "form": [{"verse": {}, "chorus": {}}]}  # not a single-key mapping
    with pytest.raises(ValueError):
        A.build_spec(bad)


# --- Thread 1b: cross-section voice-leading continuity --------------------

def test_build_chord_timeline_prev_sop_seeds_first_voicing():
    from mtheory import ChordDef
    import composition as C
    from voicing import realize_SATB

    chord = ChordDef(root_pc=0, pcs=(0, 4, 7))
    tl_seeded = C.build_chord_timeline([chord], beats_total=1.0,
                                       base_len_beats=1.0,
                                       prev_sop=72, bass_anchor=50)
    expected = realize_SATB(72, chord.root_pc, list(chord.pcs),
                            bass_pc=chord.bass_pc, bass_anchor=50)
    assert tl_seeded[0][2] == expected


def test_build_events_threads_prev_sop_between_sections(monkeypatch):
    calls = []
    orig = mg.build_chord_timeline

    def spy(*args, **kwargs):
        calls.append(kwargs.get("prev_sop"))
        return orig(*args, **kwargs)

    monkeypatch.setattr(mg, "build_chord_timeline", spy)
    spec = A.build_spec(RAW)
    A.build_events(spec)
    assert len(calls) == 2
    assert calls[0] is None       # first section starts with no lead-in
    assert calls[1] is not None   # second section is seeded from the first


# --- Thread 1c: transitions / fills at section boundaries -----------------

def test_parse_transition_fill_units():
    assert A._parse_transition_fill("1bar") == 4.0
    assert A._parse_transition_fill("2bars") == 8.0
    assert A._parse_transition_fill("0.5bar") == 2.0
    assert A._parse_transition_fill(1.5) == 6.0


def test_apply_transition_fill_replaces_tail():
    import percussion as P
    main = P.quantize_to_grid(P.parse_pattern("qk,qk,qk,qk"))
    fill = P.quantize_to_grid(P.parse_pattern("er,er,er,er,er,er,er,er"))
    drum_tl = P.build_drum_timeline_with_fills(main, None, 4.0, 0.0)

    out = A._apply_transition_fill(drum_tl, 4.0, "1bar", main, [fill])

    kept = [h for w, d, h in out if w < 3.0]
    tail = [(w, d, h) for w, d, h in out if w >= 3.0]
    assert kept  # untouched head remains
    assert tail  # fill occupies the last bar
    assert all(w >= 3.0 for w, _, _ in tail)
    assert sum(d for _, d, _ in out) == pytest.approx(4.0)


def test_transition_crash_added_at_next_section_downbeat():
    raw = {
        "title": "t", "tempo": 120,
        "defaults": {"chord_length": "q", "perc": {"main": "qk,qk,qk,qk"}},
        "sections": [
            {"name": "a", "bars": 1, "keys": "C::maj",
             "transition": {"crash": True}},
            {"name": "b", "bars": 1, "keys": "G::maj"},
        ],
    }
    spec = A.build_spec(raw)
    events, total = A.build_events(spec)
    crash_note = mg.get_drum_map()["j"]
    crash_hits = [(w, h) for k, w, _, h in events
                  if k == "drum" for hit in h if hit.note == crash_note
                  for _ in [None]]
    assert any(w == pytest.approx(4.0) for w, _ in crash_hits)



# --- Thread 1d: dynamics arc (per-section intensity) ----------------------

def test_intensity_lookup_matches_section_boundaries():
    raw = {
        "title": "t", "tempo": 120,
        "defaults": {"chord_length": "q"},
        "sections": [
            {"name": "a", "bars": 1, "keys": "C::maj",
             "dynamics": {"intensity": 0.6}},
            {"name": "b", "bars": 1, "keys": "G::maj",
             "dynamics": {"intensity": 1.2}},
        ],
    }
    spec = A.build_spec(raw)
    lookup = A.intensity_lookup(spec)
    assert lookup(0.0) == pytest.approx(0.6)
    assert lookup(3.9) == pytest.approx(0.6)
    assert lookup(4.0) == pytest.approx(1.2)   # section b starts here
    assert lookup(7.9) == pytest.approx(1.2)
    assert lookup(100.0) == pytest.approx(1.2)  # past the end: last section


def test_intensity_lookup_defaults_to_one():
    spec = A.build_spec(RAW)  # no 'dynamics' set anywhere
    lookup = A.intensity_lookup(spec)
    assert lookup(0.0) == pytest.approx(1.0)
    assert lookup(10.0) == pytest.approx(1.0)


def test_dynamics_scales_perc_fill_rate():
    raw = {
        "title": "t", "tempo": 120,
        "defaults": {"chord_length": "q",
                     "perc": {"main": "qk,qk,qk,qk",
                              "interrupters": ["ek,ek,ek,ek,ek,ek,ek,ek"],
                              "fill_rate": 0.5}},
        "sections": [
            {"name": "quiet", "bars": 1, "keys": "C::maj",
             "dynamics": {"intensity": 0.0}},
        ],
    }
    spec = A.build_spec(raw)
    events, _ = A.build_events(spec)
    # intensity 0.0 * fill_rate 0.5 => no interrupter fills should fire, so
    # every drum slot should be a plain quarter-note kick from the main
    # pattern (4 beats of section / 1 beat per main-pattern slot = 4)
    drum_events = [e for e in events if e[0] == "drum"]
    assert len(drum_events) == 4


def test_render_events_intensity_at_scales_velocity(tmp_path):
    import music_generator as mgen
    quiet_out = str(tmp_path / "quiet.mid")
    loud_out = str(tmp_path / "loud.mid")

    def make_events():
        return [("chord", 0.0, 1.0, (60, 64, 67, 48))]

    for out_path, factor in ((quiet_out, 0.4), (loud_out, 1.0)):
        midi = mgen.MidiOut(120, out_path, vel_mode_chords="uniform",
                            split_stems=True)
        mgen.render_events(midi, make_events(), intensity_at=lambda w: factor)
        midi.flush_to_end(1.0, 0.0, 1.0)
        midi.save()

    import mido
    def max_velocity(path):
        mid = mido.MidiFile(path)
        return max((m.velocity for tr in mid.tracks for m in tr
                    if m.type == "note_on"), default=0)

    assert max_velocity(quiet_out) < max_velocity(loud_out)



# --- Thread 1e: `length: {seconds}` target ---------------------------------

def _spec_seconds(spec: A.SongSpec) -> float:
    """Total real-world duration of a spec's sections, from beats + tempo."""
    total = 0.0
    for sec in spec.sections:
        chord_len = mg.DUR_MAP[sec["chord_length"]]
        seq_len = len(mg.key_roots("ostinato", sec["keys"]))
        beats = A._section_beats(sec, seq_len, chord_len)
        total += beats * 60.0 / sec["tempo"]
    return total


def test_length_seconds_loops_and_trims_to_target():
    raw = {
        "title": "t", "tempo": 120,
        "defaults": {"chord_length": "q"},
        "length": {"seconds": 10.0},
        "sections": [
            {"name": "a", "bars": 2, "keys": "C::maj"},   # 8 beats @120bpm = 4s
            {"name": "b", "bars": 2, "keys": "G::maj"},   # 8 beats @120bpm = 4s
        ],
    }
    spec = A.build_spec(raw)
    assert _spec_seconds(spec) == pytest.approx(10.0)
    # a, b, then a-loop2 trimmed to exactly the remaining 2 seconds
    names = [s["name"] for s in spec.sections]
    assert names == ["a", "b", "a-loop2"]
    assert spec.sections[-1]["bars"] == pytest.approx(1.0)  # 2s @120bpm = 4 beats = 1 bar


def test_length_seconds_respects_per_section_tempo():
    raw = {
        "title": "t", "tempo": 120,
        "defaults": {"chord_length": "q"},
        "length": {"seconds": 8.0},
        "sections": [
            {"name": "slow", "bars": 1, "tempo": 60, "keys": "C::maj"},  # 4 beats @60 = 4s
        ],
    }
    spec = A.build_spec(raw)
    assert _spec_seconds(spec) == pytest.approx(8.0)
    assert len(spec.sections) == 2  # one full pass + a trimmed loop



# --- Thread 4c: per-section mix/FX (reverb/chorus CC) ----------------------

def test_mix_emits_cc_events_per_voice_and_drums():
    raw = {
        "title": "t", "tempo": 120,
        "defaults": {"chord_length": "q"},
        "sections": [
            {"name": "a", "bars": 1, "keys": "C::maj",
             "mix": {"bass": {"reverb": 40}, "soprano": {"chorus": 20},
                     "drums": {"reverb": 10, "chorus": 5}}},
        ],
    }
    spec = A.build_spec(raw)
    events, _ = A.build_events(spec)
    cc_events = {tuple(payload) for k, _, _, payload in events if k == "cc"}
    assert ("bass", 91, 40) in cc_events
    assert ("soprano", 93, 20) in cc_events
    assert ("drums", 91, 10) in cc_events
    assert ("drums", 93, 5) in cc_events


def test_mix_absent_emits_no_cc_events():
    spec = A.build_spec(RAW)  # no 'mix' anywhere
    events, _ = A.build_events(spec)
    assert not any(k == "cc" for k, *_ in events)


def test_render_events_dispatches_cc_to_midiout(monkeypatch):
    import music_generator as mgen
    midi = mgen.MidiOut(120, split_stems=True)
    calls = []
    monkeypatch.setattr(midi, "control_change_at",
                        lambda voice, control, value, when: calls.append(
                            ("voice", voice, control, value, when)))
    monkeypatch.setattr(midi, "drum_control_change_at",
                        lambda control, value, when: calls.append(
                            ("drums", control, value, when)))
    events = [
        ("cc", 2.0, 0.0, ("bass", 91, 64)),
        ("cc", 2.0, 0.0, ("drums", 93, 32)),
    ]
    mgen.render_events(midi, events)
    assert ("voice", "bass", 91, 64, 2.0) in calls
    assert ("drums", 93, 32, 2.0) in calls


def test_transition_crash_skipped_on_last_section():
    raw = {
        "title": "t", "tempo": 120,
        "defaults": {"chord_length": "q", "perc": {"main": "qk,qk,qk,qk"}},
        "sections": [
            {"name": "a", "bars": 1, "keys": "C::maj",
             "transition": {"crash": True}},
        ],
    }
    spec = A.build_spec(raw)
    events, total = A.build_events(spec)
    crash_note = mg.get_drum_map()["j"]
    assert not any(hit.note == crash_note for k, _, _, h in events
                  if k == "drum" for hit in h)
