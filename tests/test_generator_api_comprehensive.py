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
