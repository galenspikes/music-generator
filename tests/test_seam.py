"""Tests for the engine-level seam: the disk-free builders extracted from
``main()`` so the CLI and the web API share one render path.

These pin the contract the web layer depends on — in-memory MIDI, no writes to
``output/`` — and guard the refactor that introduced them.
"""

import glob

import mido
import pytest

import music_generator as mg


def _flat_args(**over):
    args = mg.build_parser().parse_args([])
    args.mode = "ostinato"
    args.keys = "C::maj7, A::min9, D::min7, G::13"
    args.seconds = 8
    args.bpm = 120
    for k, v in over.items():
        setattr(args, k, v)
    mg.apply_arg_normalization(args)
    return args


def _notes(midifile):
    return [m for tr in midifile.tracks for m in tr
            if m.type == "note_on" and m.velocity > 0]


# --- build_parser --------------------------------------------------------------

def test_build_parser_exposes_core_flags():
    parser = mg.build_parser()
    dests = {a.dest for a in parser._actions}
    for flag in ("mode", "keys", "chords", "bpm", "instrument", "perc_main",
                 "split_stems", "voicing", "seconds"):
        assert flag in dests


def test_build_parser_defaults_are_complete():
    # parse_args([]) must succeed (nothing required) and fill every dest.
    ns = mg.build_parser().parse_args([])
    assert ns.mode == "mixed"
    assert ns.split_stems is True  # set via set_defaults
    assert ns.bpm == 120


# --- MidiOut in-memory ---------------------------------------------------------

def test_midiout_to_bytes_is_valid_midi():
    midi, _meta = mg.build_flat_midi(_flat_args())
    data = midi.to_bytes()
    assert data[:4] == b"MThd"
    # round-trips back through mido with notes
    parsed = mido.MidiFile(file=__import__("io").BytesIO(data))
    assert len(_notes(parsed)) > 0


def test_midiout_save_without_path_raises():
    out = mg.MidiOut(120, None)
    with pytest.raises(ValueError):
        out.save()


# --- build_flat_midi -----------------------------------------------------------

def test_build_flat_midi_returns_midiout_and_meta():
    midi, meta = mg.build_flat_midi(_flat_args())
    assert isinstance(midi, mg.MidiOut)
    assert "chord_family_preview_first16" in meta
    assert "perc_stages_declared" in meta


def test_build_flat_midi_writes_nothing_to_output(tmp_path):
    before = set(glob.glob(str(mg.MIDI_DIR / "**" / "*.mid"), recursive=True))
    mg.build_flat_midi(_flat_args())
    after = set(glob.glob(str(mg.MIDI_DIR / "**" / "*.mid"), recursive=True))
    assert before == after  # disk-free


def test_build_flat_midi_seeded_is_deterministic():
    import random
    random.seed(7)
    a = mg.build_flat_midi(_flat_args(seconds=10))[0].to_bytes()
    random.seed(7)
    b = mg.build_flat_midi(_flat_args(seconds=10))[0].to_bytes()
    assert a == b


def test_build_flat_midi_dense_merges_voices():
    midi, _ = mg.build_flat_midi(_flat_args(voicing="dense"))
    # dense disables split stems -> a single melodic track (+ drums track)
    melodic = [t for t in midi.mid.tracks
               if any(m.type == "note_on" for m in t)]
    assert len(melodic) <= 2


# --- apply_arg_normalization ---------------------------------------------------

def test_normalization_counterpoint_forces_split_stems():
    args = mg.build_parser().parse_args([])
    args.satb_style = "counterpoint"
    args.split_stems = False
    forced = mg.apply_arg_normalization(args)
    assert args.split_stems is True
    assert forced is True


def test_normalization_dense_disables_split_stems():
    args = mg.build_parser().parse_args([])
    args.voicing = "dense"
    args.split_stems = True
    mg.apply_arg_normalization(args)
    assert args.split_stems is False


def test_normalization_clamps_counterpoint_probs():
    args = mg.build_parser().parse_args([])
    args.satb_style = "counterpoint"
    args.counterpoint_suspension_prob = 5.0   # out of range
    args.counterpoint_anticipation_prob = -2.0
    mg.apply_arg_normalization(args)
    assert 0.0 <= args.counterpoint_suspension_prob <= 1.0
    assert 0.0 <= args.counterpoint_anticipation_prob <= 1.0


# --- build_generated (fugue/process timbre path) -------------------------------

def test_build_generated_returns_inmemory_midi():
    events = [("soprano", 0.0, 1.0, 60), ("soprano", 1.0, 1.0, 64)]
    midi = mg.build_generated(120, events, total=2.0, instrument="organ",
                              vel_chords="uniform", vel_drums="uniform")
    assert midi.to_bytes()[:4] == b"MThd"


# --- SpecError: shared builders don't leak SystemExit into the platform --------

def test_build_flat_midi_bad_voice_instrument_raises_specerror():
    args = _flat_args(voice_instrument=["bogus"])  # missing VOICE=NAME
    with pytest.raises(mg.SpecError):
        mg.build_flat_midi(args)


def test_specerror_is_ordinary_exception_not_systemexit():
    # SystemExit derives from BaseException (not Exception); SpecError must be a
    # plain Exception so the API's `except Exception` catch-all classifies it.
    assert issubclass(mg.SpecError, Exception)
    assert not issubclass(mg.SpecError, SystemExit)


# --- song_overrides_from_args: one builder, two front-end semantics ------------

def test_song_overrides_include_all_forces_ui_values():
    args = mg.build_parser().parse_args(
        ["--bpm", "111", "--instrument", "organ", "--no-perc"])
    ov = mg.song_overrides_from_args(args, lambda *a: True)
    assert ov["tempo"] == 111
    assert ov["instrument"] == "organ"
    assert ov["perc"]["main"] == ""          # --no-perc -> explicit silence
    assert ov["bass"] == {"style": "follow", "step": 0.5}


def test_song_overrides_none_set_preserves_yaml_defaults():
    args = mg.build_parser().parse_args([])
    # CLI semantics: nothing the user set -> no overrides, YAML defaults win.
    assert mg.song_overrides_from_args(args, lambda *a: False) == {}


def test_song_overrides_only_set_flag_contributes():
    args = mg.build_parser().parse_args(["--bpm", "90"])
    only_bpm = lambda dest, *flags: dest == "bpm"  # noqa: E731
    ov = mg.song_overrides_from_args(args, only_bpm)
    assert ov == {"tempo": 90}
