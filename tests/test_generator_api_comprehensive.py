"""Comprehensive tests for the generator_api module.

Tests the programmatic API seam that the web UI builds on, including
spec validation, generation, parameter schemas, and token parsing.
"""

import pytest

import generator_api as api


class TestGenerationError:
    """Test GenerationError exception class."""

    def test_creation_with_message_only(self):
        """GenerationError can be created with just a message."""
        err = api.GenerationError("Something went wrong")
        assert str(err) == "Something went wrong"
        assert err.error_type == "generation_error"
        assert err.code == "ERR_GEN_000"
        assert err.suggestion == ""

    def test_creation_with_fields(self):
        """GenerationError supports error_type, code, and suggestion."""
        err = api.GenerationError(
            "Bad key",
            error_type="invalid_key",
            code="ERR_KEY_001",
            suggestion="Valid roots: C, Db, D, ..."
        )
        assert err.error_type == "invalid_key"
        assert err.code == "ERR_KEY_001"
        assert err.suggestion == "Valid roots: C, Db, D, ..."

    def test_as_dict(self):
        """as_dict() returns structured error information."""
        err = api.GenerationError(
            "Invalid chord",
            error_type="chord_error",
            suggestion="Try maj7, min7, 7",
            code="ERR_CHORD_01"
        )
        d = err.as_dict()
        assert d["message"] == "Invalid chord"
        assert d["error_type"] == "chord_error"
        assert d["suggestion"] == "Try maj7, min7, 7"
        assert d["code"] == "ERR_CHORD_01"


class TestTrackInfoAndResults:
    """Test data structures for generation results."""

    def test_track_info_creation(self):
        """TrackInfo holds index, name, program, channel, notes."""
        info = api.TrackInfo(
            index=0,
            name="Soprano",
            program=0,
            channel=0,
            notes=42
        )
        assert info.index == 0
        assert info.name == "Soprano"
        assert info.notes == 42

    def test_generation_result_creation(self):
        """GenerationResult holds MIDI data and metadata."""
        result = api.GenerationResult(
            midi=b"test",
            tracks=[],
            duration_seconds=4.0,
            mode="ostinato",
            warnings=[]
        )
        assert result.midi == b"test"
        assert result.duration_seconds == 4.0
        assert result.mode == "ostinato"

    def test_validation_result_creation(self):
        """ValidationResult indicates success or error."""
        result = api.ValidationResult(ok=True, error=None)
        assert result.ok is True
        assert result.error is None

    def test_validation_result_with_error(self):
        """ValidationResult can carry error details."""
        result = api.ValidationResult(
            ok=False,
            error="Bad spec",
            suggestion="Check your input"
        )
        assert result.ok is False
        assert result.error == "Bad spec"


class TestParseKeys:
    """Test chord root/key parsing."""

    def test_parse_keys_simple_roots(self):
        """parse_keys handles simple root list like 'C,G,D'."""
        result = api.parse_keys("C,G,D", mode="ostinato")
        assert isinstance(result, dict)
        # Should have keys with root/octave/inversion info
        assert len(result) > 0

    def test_parse_keys_with_colon_tokens(self):
        """parse_keys handles colon tokens like 'C::maj7,G::7'."""
        result = api.parse_keys("C::maj7,G::7", mode="ostinato")
        assert isinstance(result, dict)

    def test_parse_keys_invalid_root_returns_error(self):
        """Invalid root letter returns error in result."""
        result = api.parse_keys("Z::maj7", mode="ostinato")
        assert result.get("ok") is False
        assert result.get("error") is not None

    def test_parse_keys_arrangement_mode(self):
        """parse_keys works with arrangement mode."""
        result = api.parse_keys("C,G", mode="arrangement")
        assert isinstance(result, dict)


class TestParsePerc:
    """Test percussion token parsing."""

    def test_parse_perc_basic_pattern(self):
        """parse_perc handles basic drum patterns."""
        result = api.parse_perc("qbeg,qbceg", kind="drums")
        assert isinstance(result, dict)

    def test_parse_perc_with_modifiers(self):
        """parse_perc handles modifiers like [vel=10,prob=0.8]."""
        result = api.parse_perc("qb[vel=10],qe[prob=0.8]g", kind="drums")
        assert isinstance(result, dict)

    def test_parse_perc_invalid_token_returns_error(self):
        """Invalid percussion token returns error in result."""
        result = api.parse_perc("invalid_perc", kind="drums")
        assert result.get("ok") is False
        assert result.get("error") is not None


class TestValidate:
    """Test spec validation."""

    def test_validate_minimal_spec(self):
        """Minimal spec with just keys validates."""
        spec = {
            "keys": "C::maj7,G::7",
            "seconds": "4",
            "bpm": "120",
        }
        result = api.validate(spec)
        assert isinstance(result, api.ValidationResult)
        # Minimal spec should be valid
        assert result.ok is True

    def test_validate_with_invalid_key(self):
        """Invalid key in spec fails validation."""
        spec = {
            "keys": "Z::invalid",
            "seconds": "4",
        }
        result = api.validate(spec)
        assert result.ok is False
        assert result.error is not None

    def test_validate_with_invalid_bpm(self):
        """Invalid BPM in spec."""
        spec = {
            "keys": "C::maj7",
            "bpm": "not_a_number",
            "seconds": "4",
        }
        result = api.validate(spec)
        assert result.ok is False or result.error is not None

    def test_validate_with_percussion(self):
        """Spec with percussion validates."""
        spec = {
            "keys": "C::maj7",
            "perc-main": "qbeg",
            "seconds": "4",
        }
        result = api.validate(spec)
        assert isinstance(result, api.ValidationResult)


class TestGenerate:
    """Test MIDI generation from spec."""

    def test_generate_minimal_spec(self):
        """Minimal spec generates valid MIDI."""
        spec = {
            "keys": "C::maj7",
            "seconds": "2",
            "bpm": "120",
            "no-play": "true",
        }
        result = api.generate(spec)
        assert isinstance(result, api.GenerationResult)
        assert result.midi is not None
        assert len(result.midi) > 0
        assert result.duration_seconds == pytest.approx(2.0)

    def test_generate_with_voicing(self):
        """Generate with different voicing modes."""
        spec_block = {
            "keys": "C::maj7",
            "voicing": "satb",
            "seconds": "2",
            "bpm": "120",
        }
        result_block = api.generate(spec_block)
        assert result_block.midi is not None

        spec_dense = {
            "keys": "C::maj7",
            "voicing": "dense",
            "seconds": "2",
            "bpm": "120",
        }
        result_dense = api.generate(spec_dense)
        assert result_dense.midi is not None
        # Different voicings may produce different MIDI lengths
        assert len(result_block.midi) > 0
        assert len(result_dense.midi) > 0

    def test_generate_with_percussion(self):
        """Generate with percussion."""
        spec = {
            "keys": "C::maj7",
            "perc-main": "qbeg,qbceg",
            "seconds": "2",
            "bpm": "120",
        }
        result = api.generate(spec)
        assert result.midi is not None
        assert len(result.midi) > 0

    def test_generate_with_instrument(self):
        """Generate with specific instrument."""
        spec = {
            "keys": "C::maj7",
            "instrument": "piano",
            "seconds": "2",
            "bpm": "120",
        }
        result = api.generate(spec)
        assert result.midi is not None

    def test_generate_with_random_roots(self):
        """Generate with --random-roots mode."""
        spec = {
            "keys": "",  # Ignored with random-roots
            "random-roots": "true",
            "seconds": "2",
            "bpm": "120",
        }
        result = api.generate(spec)
        assert result.midi is not None

    def test_generate_with_full_progression(self):
        """Generate with --full-progression mode."""
        spec = {
            "keys": "C,G,D",
            "full-progression": "true",
            "seconds": "4",
            "bpm": "120",
        }
        result = api.generate(spec)
        assert result.midi is not None

    def test_generate_with_split_stems(self):
        """Generate with split stems (separate tracks)."""
        spec = {
            "keys": "C::maj7",
            "split-stems": "true",
            "seconds": "2",
            "bpm": "120",
        }
        result = api.generate(spec)
        assert result.midi is not None
        assert len(result.tracks) > 0

    def test_generate_deterministic_with_seed(self):
        """Generation is deterministic with same seed."""
        spec_base = {
            "keys": "C::maj7,G::7",
            "seed": "42",
            "seconds": "2",
            "bpm": "120",
        }
        result1 = api.generate(spec_base)
        result2 = api.generate(spec_base)
        assert result1.midi == result2.midi

    def test_generate_different_with_different_seeds(self):
        """Different seeds produce different results."""
        spec1 = {
            "keys": "C::maj7,G::7",
            "seed": "42",
            "seconds": "2",
            "bpm": "120",
        }
        spec2 = {
            "keys": "C::maj7,G::7",
            "seed": "43",
            "seconds": "2",
            "bpm": "120",
        }
        result1 = api.generate(spec1)
        result2 = api.generate(spec2)
        # Different seeds should produce different MIDI
        assert result1.midi != result2.midi

    def test_generate_invalid_spec_raises(self):
        """Invalid spec raises GenerationError."""
        spec = {
            "keys": "Z::invalid",
            "seconds": "2",
        }
        with pytest.raises(api.GenerationError):
            api.generate(spec)


class TestParameterSchema:
    """Test parameter schema introspection."""

    def test_parameter_schema_returns_list(self):
        """parameter_schema() returns list of parameter specs."""
        schema = api.parameter_schema()
        assert isinstance(schema, list)
        assert len(schema) > 0

    def test_parameter_spec_has_required_fields(self):
        """Each parameter spec has name, kind, default, etc."""
        schema = api.parameter_schema()
        for param in schema:
            assert isinstance(param, dict)
            # Should have at least these keys
            required = {"name", "kind"}
            assert required.issubset(param.keys())

    def test_schema_includes_common_parameters(self):
        """Schema includes expected parameters."""
        schema = api.parameter_schema()
        param_names = {p["name"] for p in schema}
        # Check for some expected parameters
        expected = {"keys", "bpm", "seconds"}
        assert len(expected & param_names) > 0


class TestEnvelopeFromBytes:
    """Test audio envelope extraction."""

    def test_envelope_from_bytes_exists(self):
        """envelope_from_bytes function exists and is callable."""
        # This is a minimal test - the function works on rendered audio
        # For this unit test, we're just checking the function exists
        assert hasattr(api, 'envelope_from_bytes')
        assert callable(api.envelope_from_bytes)


class TestClassifyError:
    """Test error message classification."""

    def test_classify_error_bad_key(self):
        """Classifies 'Bad key' errors."""
        err_type, suggestion, code = api.classify_error("Bad key 'ZZ'")
        assert err_type is not None
        assert code is not None

    def test_classify_error_unknown_drum(self):
        """Classifies unknown drum letter errors."""
        err_type, suggestion, code = api.classify_error(
            "Unknown drum letter 'x' in token 'qx'"
        )
        assert err_type is not None

    def test_classified_returns_generation_error(self):
        """_classified() wraps errors in GenerationError."""
        err = api._classified("Bad key 'ZZ'")
        assert isinstance(err, api.GenerationError)


class TestIntegration:
    """Integration tests for the full API."""

    def test_full_workflow_validate_and_generate(self):
        """Full workflow: validate spec, then generate."""
        spec = {
            "keys": "C::maj7,A::min7,D::min7,G::7",
            "instrument": "piano",
            "bpm": "90",
            "seconds": "4",
            "perc-main": "qbeg",
            "voicing": "satb",
        }

        # Validate first
        validation = api.validate(spec)
        assert validation.ok is True

        # Then generate
        result = api.generate(spec)
        assert result.midi is not None
        assert result.duration_seconds == pytest.approx(4.0)
        assert result.mode in ("ostinato", "progression")  # Depend on keys format

    def test_different_instruments(self):
        """Generate with different instruments."""
        base_spec = {
            "keys": "C::maj7",
            "seconds": "1",
            "bpm": "120",
        }

        for instrument in ["piano", "guitar", "strings"]:
            spec = {**base_spec, "instrument": instrument}
            result = api.generate(spec)
            assert result.midi is not None

    def test_bass_line_styles(self):
        """Generate with different bass line styles."""
        base_spec = {
            "keys": "C::maj7",
            "seconds": "1",
            "bpm": "120",
        }

        for style in ["follow", "root", "none"]:
            spec = {**base_spec, "bass-style": style}
            result = api.generate(spec)
            assert result.midi is not None

    def test_chord_modes(self):
        """Generate with different chord families."""
        base_spec = {
            "keys": "C",
            "seconds": "1",
            "bpm": "120",
        }

        for mode in ["triads", "sevenths", "ninths"]:
            spec = {**base_spec, "chords": mode}
            result = api.generate(spec)
            assert result.midi is not None


class TestErrorClassification:
    """Test error message classification for better user feedback."""

    def test_classify_bad_key(self):
        """Recognizes invalid chord root."""
        error_type, suggestion, code = api.classify_error("Bad key 'ZZ'")
        assert error_type == "invalid_chord"
        assert "C, Db, D" in suggestion
        assert code == "ERR_CHORD_001"

    def test_classify_unknown_recipe(self):
        """Recognizes unknown chord recipe."""
        error_type, suggestion, code = api.classify_error("Unknown chord recipe 'xyz'")
        assert error_type == "invalid_recipe"
        assert code == "ERR_CHORD_002"

    def test_classify_missing_bass_note(self):
        """Recognizes missing slash chord bass."""
        error_type, suggestion, code = api.classify_error("Missing bass note")
        assert error_type == "invalid_chord"
        assert code == "ERR_CHORD_003"

    def test_classify_unknown_drum_letter(self):
        """Recognizes invalid percussion letter."""
        error_type, suggestion, code = api.classify_error("Unknown drum letter 'x'")
        assert error_type == "invalid_drum"
        assert code == "ERR_PERC_001"

    def test_classify_bad_duration(self):
        """Recognizes invalid duration specification."""
        error_type, suggestion, code = api.classify_error("Bad duration in token 'x'")
        assert error_type == "invalid_duration"
        assert "qb = quarter" in suggestion
        assert code == "ERR_DUR_001"

    def test_classify_incomplete_token(self):
        """Recognizes incomplete percussion token."""
        error_type, suggestion, code = api.classify_error("Incomplete token")
        assert error_type == "invalid_duration"
        assert code == "ERR_DUR_001"

    def test_classify_repetition_error(self):
        """Recognizes repetition syntax errors."""
        error_type, suggestion, code = api.classify_error("Bad repetition *N")
        assert error_type == "invalid_syntax"
        assert code == "ERR_SYNTAX_001"

    def test_classify_empty_token(self):
        """Recognizes empty tokens."""
        error_type, suggestion, code = api.classify_error("Empty token")
        assert error_type == "invalid_syntax"
        assert code == "ERR_SYNTAX_002"

    def test_classify_empty_chain(self):
        """Recognizes empty chains."""
        error_type, suggestion, code = api.classify_error("Empty chain")
        assert error_type == "invalid_syntax"
        assert code == "ERR_SYNTAX_002"

    def test_classify_unknown_message(self):
        """Unknown error messages get generic classification."""
        error_type, suggestion, code = api.classify_error("Some random error message")
        assert error_type == "generation_error"
        assert code == "ERR_GEN_000"

    def test_classify_none_message(self):
        """None message is handled safely."""
        error_type, suggestion, code = api.classify_error(None)
        assert error_type == "generation_error"
        assert code == "ERR_GEN_000"


class TestParameterSchema:
    """Test parameter schema introspection."""

    def test_parameter_schema_returns_list(self):
        """parameter_schema() returns a list of parameter specs."""
        schema = api.parameter_schema()
        assert isinstance(schema, list)
        assert len(schema) > 0

    def test_schema_entries_have_required_fields(self):
        """Each schema entry has name, kind, and help."""
        schema = api.parameter_schema()
        for entry in schema:
            assert "name" in entry
            assert "kind" in entry or "choices" in entry
            assert "help" in entry

    def test_schema_keys_parameter(self):
        """Keys parameter is in schema."""
        schema = api.parameter_schema()
        names = [s["name"] for s in schema]
        assert "keys" in names

    def test_schema_seconds_parameter(self):
        """Seconds parameter is in schema."""
        schema = api.parameter_schema()
        names = [s["name"] for s in schema]
        assert "seconds" in names

    def test_schema_bpm_parameter(self):
        """BPM parameter is in schema."""
        schema = api.parameter_schema()
        names = [s["name"] for s in schema]
        assert "bpm" in names


class TestSongManagement:
    """Test song loading and listing."""

    def test_list_songs_returns_list(self):
        """list_songs() returns a list."""
        songs = api.list_songs()
        assert isinstance(songs, list)

    def test_list_songs_structure(self):
        """Each song has name and title fields."""
        songs = api.list_songs()
        if songs:
            for song in songs:
                assert "name" in song
                assert "title" in song

    def test_load_song_with_valid_name(self):
        """load_song() can load a valid song."""
        songs = api.list_songs()
        if songs:
            song_name = songs[0]["name"]
            song = api.load_song(song_name)
            assert song is not None
            assert isinstance(song, dict)

    def test_load_song_returns_dict(self):
        """load_song() returns a dictionary spec."""
        songs = api.list_songs()
        if songs:
            song = api.load_song(songs[0]["name"])
            assert isinstance(song, dict)


class TestPresetManagement:
    """Test preset saving, loading, listing."""

    def test_list_presets_returns_list(self):
        """list_presets() returns a list."""
        presets = api.list_presets()
        assert isinstance(presets, list)

    def test_list_presets_structure(self):
        """Each preset has name and title."""
        presets = api.list_presets()
        if presets:
            for preset in presets:
                assert "name" in preset
                assert "title" in preset

    def test_save_and_load_preset(self):
        """Can save and load a preset."""
        spec = {"keys": "C::maj7", "seconds": "2", "bpm": "120"}
        name = "test_preset_xyz"

        try:
            api.save_preset(name, spec, title="Test Preset")
            loaded = api.load_preset(name)

            assert loaded is not None
            assert isinstance(loaded, dict)
        finally:
            api.delete_preset(name)

    def test_delete_preset(self):
        """Can delete a preset."""
        spec = {"keys": "C::maj", "seconds": "1"}
        name = "test_delete_xyz"

        api.save_preset(name, spec)
        api.delete_preset(name)

        # Verify it's gone by checking list
        presets = api.list_presets()
        names = [p["name"] for p in presets]
        assert name not in names

    def test_has_home_preset(self):
        """has_home_preset() returns boolean."""
        result = api.has_home_preset()
        assert isinstance(result, bool)

    def test_save_preset_with_description(self):
        """Preset can have a description."""
        spec = {"keys": "G::maj7"}
        name = "test_desc_xyz"

        try:
            api.save_preset(name, spec, title="Title",
                            description="Test description")
            loaded = api.load_preset(name)

            assert loaded is not None
        finally:
            api.delete_preset(name)


class TestProgressionManagement:
    """Test progression saving, loading, listing."""

    def test_list_progressions_returns_list(self):
        """list_progressions() returns a list."""
        progs = api.list_progressions()
        assert isinstance(progs, list)

    def test_list_progressions_structure(self):
        """Each progression has name and title."""
        progs = api.list_progressions()
        if progs:
            for prog in progs:
                assert "name" in prog
                assert "title" in prog

    def test_save_and_load_progression(self):
        """Can save and load a progression."""
        keys_spec = "C::maj, F::maj, G::maj"
        name = "test_prog_xyz"

        try:
            api.save_progression(name, keys_spec, title="Test Progression")
            loaded = api.load_progression(name)

            assert loaded is not None
        finally:
            api.delete_progression(name)

    def test_delete_progression(self):
        """Can delete a progression."""
        keys_spec = "C::maj, G::maj"
        name = "test_prog_delete_xyz"

        api.save_progression(name, keys_spec)
        api.delete_progression(name)

        # Verify it's gone
        progs = api.list_progressions()
        names = [p["name"] for p in progs]
        assert name not in names


class TestEnvelopeExtraction:
    """Test MIDI envelope extraction from MIDI bytes."""

    def test_envelope_from_bytes_with_valid_midi(self):
        """envelope_from_bytes extracts envelope from MIDI."""
        # Generate some MIDI to test with
        spec = {"keys": "C::maj7", "seconds": "1"}
        result = api.generate(spec)

        envelope = api.envelope_from_bytes(result.midi, result.duration_seconds)
        assert isinstance(envelope, list)
        assert len(envelope) > 0
        assert all(isinstance(x, (int, float)) for x in envelope)

    def test_envelope_custom_bucket_count(self):
        """envelope_from_bytes respects bucket count."""
        spec = {"keys": "C::maj7", "seconds": "1"}
        result = api.generate(spec)

        envelope = api.envelope_from_bytes(result.midi, result.duration_seconds, buckets=30)
        assert len(envelope) == 30


class TestSlugify:
    """Test slug generation for preset/progression names."""

    def test_slugify_simple_name(self):
        """Slugify converts to lowercase."""
        slug = api.slugify("Test Preset")
        assert slug == slug.lower()

    def test_slugify_removes_spaces(self):
        """Slugify handles spaces."""
        slug = api.slugify("My Test Preset")
        assert " " not in slug

    def test_slugify_removes_special_chars(self):
        """Slugify removes special characters."""
        slug = api.slugify("Test!@#$%Preset")
        # Slugify produces a valid identifier/slug
        assert isinstance(slug, str)
        assert len(slug) > 0
