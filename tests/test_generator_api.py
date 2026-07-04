"""Tests for ``generator_api`` — the programmatic seam the web UI builds on:
generate / validate / parse_keys / parse_perc / parameter_schema.
"""

import glob
import io

import mido
import pytest

import generator_api as api
import music_generator as mg


def _midi_notes(data: bytes):
    parsed = mido.MidiFile(file=io.BytesIO(data))
    return [m for tr in parsed.tracks for m in tr
            if m.type == "note_on" and m.velocity > 0]


# --- generate ------------------------------------------------------------------

def test_generate_flat_returns_result():
    r = api.generate({"mode": "ostinato", "keys": "C::maj7, A::min9, G::13",
                      "seconds": 8, "bpm": 120})
    assert r.midi[:4] == b"MThd"
    assert r.mode == "ostinato"
    assert r.duration_seconds == 8
    assert len(_midi_notes(r.midi)) > 0
    names = {t.name for t in r.tracks}
    assert {"soprano", "alto", "tenor", "bass", "drums"} <= names


def test_generate_dense_collapses_to_ensemble():
    r = api.generate({"mode": "ostinato", "keys": "C::13, F::maj9",
                      "voicing": "dense", "seconds": 6})
    names = [t.name for t in r.tracks]
    assert "ensemble" in names
    assert "soprano" not in names


def test_generate_fugue():
    r = api.generate({"fugue": "__default__", "melody_key": "C",
                      "melody_mode": "major", "instrument": "organ"})
    assert r.mode == "fugue"
    assert len(_midi_notes(r.midi)) > 0


def test_generate_process():
    r = api.generate({"process": "phase",
                      "process_cell": "e1 e2 e3 e5 e7 e5 e3 e2",
                      "melody_key": "C"})
    assert r.mode == "process:phase"
    assert len(_midi_notes(r.midi)) > 0


def test_generate_song_roundtrip(tmp_path):
    r = api.generate({"song": "songs/kiss.yml"})
    assert r.mode == "song"
    assert r.midi[:4] == b"MThd"


def test_generate_bad_recipe_raises():
    with pytest.raises(api.GenerationError):
        api.generate({"mode": "ostinato", "keys": "C::definitely_not_a_recipe"})


def test_generate_is_disk_free():
    before = set(glob.glob(str(mg.MIDI_DIR / "**" / "*.mid"), recursive=True))
    api.generate({"mode": "ostinato", "keys": "C::maj7", "seconds": 6})
    after = set(glob.glob(str(mg.MIDI_DIR / "**" / "*.mid"), recursive=True))
    assert before == after


def test_generate_seeded_is_deterministic():
    spec = {"mode": "ostinato", "keys": "C::maj7, G::13", "seconds": 8,
            "seed": 123, "velocity_mode_chords": "human"}
    assert api.generate(spec).midi == api.generate(spec).midi


# --- validate ------------------------------------------------------------------

def test_validate_ok_and_error():
    assert api.validate({"mode": "ostinato", "keys": "C::maj7"}).ok is True
    bad = api.validate({"mode": "ostinato", "keys": "C::nope"})
    assert bad.ok is False
    assert "nope" in bad.error


# --- parse_keys ----------------------------------------------------------------

def test_parse_keys_labels_and_notes():
    r = api.parse_keys("C::maj7, A::min9")
    assert r["ok"] is True
    assert [c["label"] for c in r["chords"]] == ["Cmaj7", "Amin9"]
    assert r["chords"][0]["notes"] == ["C", "E", "G", "B"]


def test_parse_keys_slash_bass():
    r = api.parse_keys("G::maj/C")
    c = r["chords"][0]
    assert c["bass"] == "C"
    assert c["label"] == "Gmaj/C"


def test_parse_keys_segments_and_total():
    r = api.parse_keys("[A, G]*16, C::maj7, F::maj9")
    assert r["total"] == 34
    groups = [s for s in r["segments"] if s["type"] == "group"]
    assert groups and groups[0]["reps"] == 16
    assert [c["label"] for c in groups[0]["chords"]] == ["A", "G"]


def test_parse_keys_bare_roots_have_no_notes():
    r = api.parse_keys("C, G, Bb")
    assert all(c["notes"] == [] and c["bare"] for c in r["chords"])


def test_parse_keys_error_pinpoints_token():
    r = api.parse_keys("C::maj7, A::bogus, G::13")
    assert r["ok"] is False
    assert "bogus" in r["error"]
    assert r["error_index"] == 1


# --- parse_perc ----------------------------------------------------------------

def test_parse_perc_drums_friendly_names():
    r = api.parse_perc("qb, eg, er")
    assert r["ok"] is True
    toks = r["tokens"]
    assert toks[0]["hits"] == ["Bass Drum 1"]
    assert toks[1]["hits"] == ["Closed Hi-Hat"]
    assert toks[2]["rest"] is True


def test_parse_perc_modifier_block_not_split():
    # the comma inside [vel+10,prob0.5] must not split the token
    r = api.parse_perc("qk[vel+10,prob0.5]sh, qb")
    assert r["ok"] is True
    assert len(r["tokens"]) == 2
    assert len(r["tokens"][0]["hits"]) == 3


def test_parse_perc_bad_letter_flags_token():
    r = api.parse_perc("qb, q@, qc")
    assert r["ok"] is False
    assert r["tokens"][1]["ok"] is False


def test_parse_perc_chord_kind():
    r = api.parse_perc("ec, er, sc", kind="chord")
    assert r["ok"] is True
    assert r["tokens"][0]["hits"] == ["chord"]
    assert r["tokens"][1]["rest"] is True
    bad = api.parse_perc("eZ", kind="chord")
    assert bad["ok"] is False


# --- parameter_schema ----------------------------------------------------------

def test_schema_covers_every_parser_flag_except_hidden_baggage():
    # Every real instrument control is auto-derived and never silently
    # dropped — except the deliberate HIDDEN_PARAMS baggage cut
    # (controllability-audit.md): mode, process/fugue, CLI/render plumbing.
    schema = api.parameter_schema()
    schema_names = {p["name"] for p in schema}
    parser_dests = {a.dest for a in mg.build_parser()._actions
                    if a.dest != "help"}
    assert schema_names == parser_dests - api.HIDDEN_PARAMS
    assert schema_names.isdisjoint(api.HIDDEN_PARAMS)


def test_hidden_params_still_work_as_spec_keys():
    # Hidden from the rack, but not actually removed: the CLI and song YAML
    # still use these, so they must remain valid namespace attributes.
    ns = vars(mg.build_parser().parse_args([]))
    for name in api.HIDDEN_PARAMS:
        assert name in ns


def test_schema_entries_are_well_formed():
    for p in api.parameter_schema():
        assert p["name"] and p["kind"] and p["control"] and p["group"]


def test_schema_known_controls():
    by = {p["name"]: p for p in api.parameter_schema()}
    assert by["keys"]["control"] == "text"
    assert by["chords"]["kind"] == "multichoice"
    assert by["bpm"]["kind"] == "int"
    assert by["split_stems"]["kind"] == "bool"
    assert by["gain"]["kind"] == "float"


def test_schema_names_are_valid_spec_keys():
    # every schema name must be a real attribute on the parsed namespace,
    # so the frontend can round-trip values straight into a generate() spec.
    ns = vars(mg.build_parser().parse_args([]))
    for p in api.parameter_schema():
        assert p["name"] in ns
