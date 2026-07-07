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


def test_generate_accepts_inline_song_yaml_text():
    # The lead-sheet importer's path: raw song.yml text in the spec, never
    # written anywhere durable -- an alternative to "song" (a file path).
    yml_text = (
        "title: Inline Test\ntempo: 100\n"
        "sections:\n  - {name: A, keys: 'C::maj7, F::maj7'}\n"
    )
    r = api.generate({"song_yaml": yml_text})
    assert r.mode == "song"
    assert r.midi[:4] == b"MThd"
    assert len(_midi_notes(r.midi)) > 0


def test_generate_song_no_perc_silences_drums():
    # gap-analysis I1, song-path regression: "no_perc"/explicit-empty perc_main
    # used to be dropped by a truthy check when forwarding UI overrides into
    # the arrangement, so a song always kept its own YAML drum pattern
    # regardless of what the UI asked for.
    with_drums = api.generate({"song": "songs/kiss.yml"})
    assert any(m.channel == mg.DRUM_CH for m in _midi_notes(with_drums.midi))

    silenced = api.generate({"song": "songs/kiss.yml", "no_perc": True})
    assert not any(m.channel == mg.DRUM_CH for m in _midi_notes(silenced.midi))


def test_generate_bad_recipe_raises():
    with pytest.raises(api.GenerationError):
        api.generate({"mode": "ostinato", "keys": "C::definitely_not_a_recipe"})


# --- structured errors ---------------------------------------------------------

def test_generation_error_is_structured_with_suggestion_and_code():
    with pytest.raises(api.GenerationError) as exc_info:
        api.generate({"mode": "ostinato", "keys": "ZZ::maj7"})
    exc = exc_info.value
    d = exc.as_dict()
    assert d["error_type"] == "invalid_chord"
    assert d["code"] == "ERR_CHORD_001"
    assert d["message"]  # a human message survives
    assert "C, Db, D" in d["suggestion"]  # actionable list of valid roots


def test_generation_error_classifies_bad_recipe():
    with pytest.raises(api.GenerationError) as exc_info:
        api.generate({"mode": "ostinato", "keys": "C::definitely_not_a_recipe"})
    d = exc_info.value.as_dict()
    assert d["error_type"] == "invalid_recipe"
    assert d["suggestion"]


def test_bare_generation_error_still_works():
    # The plain constructor (used deep in the engine / for songs & presets)
    # keeps a safe generic classification — nothing to migrate.
    exc = api.GenerationError("something went sideways")
    d = exc.as_dict()
    assert d["message"] == "something went sideways"
    assert d["error_type"] == "generation_error"
    assert d["suggestion"] == ""


def test_classify_error_covers_the_common_token_mistakes():
    assert api.classify_error("Bad key 'QQ'")[0] == "invalid_chord"
    assert api.classify_error("Unknown drum letter '1' in token 'q1'")[0] == "invalid_drum"
    assert api.classify_error("Bad duration in token '2b'")[0] == "invalid_duration"
    assert api.classify_error("Unknown keys preset 'nope'")[0] == "invalid_preset"
    # every branch returns a non-empty (type, suggestion, code) triple
    for msg in ["Bad key 'x'", "recipe boom", "Unknown drum letter 'z'",
                "Bad duration in token 'q'", "whatever else"]:
        etype, suggestion, code = api.classify_error(msg)
        assert etype and suggestion and code


def test_generate_is_disk_free():
    before = set(glob.glob(str(mg.MIDI_DIR / "**" / "*.mid"), recursive=True))
    api.generate({"mode": "ostinato", "keys": "C::maj7", "seconds": 6})
    after = set(glob.glob(str(mg.MIDI_DIR / "**" / "*.mid"), recursive=True))
    assert before == after


def test_generate_returns_a_bucketed_envelope():
    r = api.generate({"mode": "ostinato", "keys": "C::maj7, A::min7", "seconds": 8,
                      "seed": 1})
    assert len(r.envelope) == 60
    assert all(0.0 <= v <= 1.0 for v in r.envelope)
    assert max(r.envelope) == 1.0  # normalized to its own peak


def test_envelope_from_bytes_empty_when_duration_zero():
    r = api.generate({"mode": "ostinato", "keys": "C::maj7", "seconds": 4, "seed": 1})
    assert api.envelope_from_bytes(r.midi, 0.0) == [0.0] * 60


def test_envelope_bucket_count_is_configurable():
    r = api.generate({"mode": "ostinato", "keys": "C::maj7", "seconds": 4, "seed": 1})
    assert len(api.envelope_from_bytes(r.midi, r.duration_seconds, buckets=10)) == 10


def test_generate_song_includes_envelope():
    r = api.generate({"song": "songs/kiss.yml"})
    assert len(r.envelope) == 60
    assert max(r.envelope) == 1.0


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


def test_validate_surfaces_suggestion_and_type():
    bad = api.validate({"mode": "ostinato", "keys": "ZZ::maj7"})
    d = bad.as_dict()
    assert d["ok"] is False
    assert d["error_type"] == "invalid_chord"
    assert d["suggestion"]


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


def test_parse_keys_exposes_pitch_classes_for_client_audio():
    # root_pc/pcs/bass_pc are what a client-side synth realizes into concrete
    # MIDI notes without re-parsing note-name strings (see chordNotes.js).
    c = api.parse_keys("C::maj7")["chords"][0]
    assert c["root_pc"] == 0
    assert c["pcs"] == [0, 4, 7, 11]
    assert c["bass_pc"] is None

    slash = api.parse_keys("G::maj/C")["chords"][0]
    assert slash["root_pc"] == 7
    assert slash["bass_pc"] == 0


def test_parse_keys_bare_root_has_no_pitch_classes():
    c = api.parse_keys("C")["chords"][0]
    assert c["pcs"] == []
    assert c["bass_pc"] is None


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
    # a suggestion accompanies the first error so the editor can hint a fix
    assert "drum letters" in r["suggestion"].lower()


def test_parse_perc_ok_has_no_suggestion():
    r = api.parse_perc("qb, eg, qc, eg")
    assert r["ok"] is True
    assert r["suggestion"] is None


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
    assert by["chord_fill_rate"]["kind"] == "float"


def test_schema_has_no_dead_fluidsynth_controls():
    # gain/reverb/chorus/poly used to be knobs in the webapp's Render panel
    # that did nothing -- only referenced in a commented-out, unreachable
    # FluidSynth-launch block. render.py (not music_generator.py) is the real
    # audio-rendering path and has its own independent --fx/--sf2 handling.
    names = {p["name"] for p in api.parameter_schema()}
    assert not ({"gain", "reverb", "chorus", "poly"} & names)


def test_schema_names_are_valid_spec_keys():
    # every schema name must be a real attribute on the parsed namespace,
    # so the frontend can round-trip values straight into a generate() spec.
    ns = vars(mg.build_parser().parse_args([]))
    for p in api.parameter_schema():
        assert p["name"] in ns


# --- presets (Thread B) ---------------------------------------------------------

@pytest.fixture
def presets_dir(tmp_path, monkeypatch):
    d = tmp_path / "presets" / "user"
    monkeypatch.setattr(api, "PRESETS_DIR", d)
    return d


def test_slugify_preserves_underscore_names():
    # existing songs/*.yml filenames (four_organs, girl_from_ipanema, ...) must
    # round-trip unchanged, since load_song/load_preset re-slugify on read.
    assert api.slugify("four_organs") == "four_organs"
    assert api.slugify("Kiss") == "kiss"


def test_slugify_sanitizes_unsafe_characters():
    assert api.slugify("My Cool Groove!") == "my-cool-groove"
    assert api.slugify("  spaced  ") == "spaced"
    assert api.slugify("") == "untitled"


def test_slugify_neutralizes_path_traversal():
    slug = api.slugify("../../../etc/passwd")
    assert "/" not in slug and ".." not in slug


def test_save_load_delete_preset_roundtrip(presets_dir):
    api.save_preset("my-groove", {"keys": "C::maj7"}, title="My Groove")
    assert api.load_preset("my-groove") == {"keys": "C::maj7"}
    names = {p["name"] for p in api.list_presets()}
    assert "my-groove" in names

    api.delete_preset("my-groove")
    assert not (presets_dir / "my-groove.json").exists()
    with pytest.raises(api.GenerationError):
        api.load_preset("my-groove")


def test_delete_missing_preset_is_not_an_error(presets_dir):
    api.delete_preset("never-existed")  # must not raise


def test_save_preset_name_is_slugified_on_disk(presets_dir):
    api.save_preset("My Cool Groove!", {"keys": "C"})
    assert (presets_dir / "my-cool-groove.json").exists()


def test_load_preset_rejects_path_traversal(presets_dir):
    # the attempted escape resolves to a slug ("etc-passwd") that simply
    # doesn't exist as a saved preset -- it must not read/write outside
    # PRESETS_DIR under any circumstance.
    with pytest.raises(api.GenerationError):
        api.load_preset("../../../etc/passwd")


def test_save_preset_path_traversal_cannot_write_outside_presets_dir(tmp_path, monkeypatch):
    # The real proof: reading a bogus traversed path would 404 "not found"
    # even without sanitization, since nothing exists there anyway. Writing
    # is the actual exploit surface -- confirm a traversal-style name can't
    # make save_preset land a file outside PRESETS_DIR.
    sandbox = tmp_path / "sandbox" / "presets"
    monkeypatch.setattr(api, "PRESETS_DIR", sandbox)
    escape_target = tmp_path / "escaped.json"

    api.save_preset("../../escaped", {"keys": "C"})

    assert not escape_target.exists()
    assert list(sandbox.glob("*.json"))  # landed safely inside instead


def test_home_preset_detection(presets_dir):
    assert api.has_home_preset() is False
    api.save_preset(api.HOME_PRESET_NAME, {"keys": "C::maj7"})
    assert api.has_home_preset() is True


# --- chord progressions (standalone Chord Recipes app) --------------------------

@pytest.fixture
def progressions_dir(tmp_path, monkeypatch):
    d = tmp_path / "presets" / "progressions"
    monkeypatch.setattr(api, "PROGRESSIONS_DIR", d)
    return d


def test_save_load_delete_progression_roundtrip(progressions_dir):
    saved = api.save_progression(
        "ii-v-i", "D::min7, G::7, C::maj7", title="ii-V-I turnaround",
        tags=["jazz"], tempo=96,
    )
    assert saved["keys"] == "D::min7, G::7, C::maj7"

    loaded = api.load_progression("ii-v-i")
    assert loaded["title"] == "ii-V-I turnaround"
    assert loaded["tags"] == ["jazz"]
    assert loaded["tempo"] == 96

    names = {p["name"] for p in api.list_progressions()}
    assert "ii-v-i" in names

    api.delete_progression("ii-v-i")
    assert not (progressions_dir / "ii-v-i.json").exists()
    with pytest.raises(api.GenerationError):
        api.load_progression("ii-v-i")


def test_delete_missing_progression_is_not_an_error(progressions_dir):
    api.delete_progression("never-existed")  # must not raise


def test_progression_name_is_slugified_on_disk(progressions_dir):
    api.save_progression("My Cool Vamp!", "C::maj7")
    assert (progressions_dir / "my-cool-vamp.json").exists()


def test_load_progression_rejects_path_traversal(progressions_dir):
    with pytest.raises(api.GenerationError):
        api.load_progression("../../../etc/passwd")


def test_save_progression_path_traversal_cannot_write_outside_progressions_dir(tmp_path, monkeypatch):
    sandbox = tmp_path / "sandbox" / "progressions"
    monkeypatch.setattr(api, "PROGRESSIONS_DIR", sandbox)
    escape_target = tmp_path / "escaped.json"

    api.save_progression("../../escaped", "C::maj7")

    assert not escape_target.exists()
    assert list(sandbox.glob("*.json"))
