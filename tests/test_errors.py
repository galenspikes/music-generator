"""Typed DSL exceptions (errors.py) and their classification at the API
boundary (generator_api.classify_exception).

The contract under test: parsers raise errors.* subclasses of ValueError, and
the API classifies by exception *type* — not by pattern-matching the message
string — so rewording a message can never break its classification.
"""
import pytest

import errors
import generator_api as api
import mtheory
import percussion
import tokens


class TestHierarchy:
    def test_all_are_value_errors(self):
        """Every typed error is a ValueError, so existing handlers keep working."""
        for name in errors.__all__:
            assert issubclass(getattr(errors, name), ValueError)

    def test_all_carry_classification(self):
        for name in errors.__all__:
            klass = getattr(errors, name)
            assert isinstance(klass.error_type, str) and klass.error_type
            assert klass.code.startswith("ERR_")


class TestParsersRaiseTypedErrors:
    def test_bad_key_bare_root(self):
        with pytest.raises(errors.InvalidKeyError):
            tokens.key_roots("ostinato", "ZZ")

    def test_bad_key_name(self):
        with pytest.raises(errors.InvalidKeyError):
            mtheory.parse_key_name("Q#x")

    def test_empty_key_name(self):
        with pytest.raises(errors.EmptyTokenError):
            mtheory.parse_key_name("   ")

    def test_unknown_recipe(self):
        with pytest.raises(errors.InvalidRecipeError):
            tokens.parse_colon_key_token("C::nosuchrecipe")

    def test_missing_slash_bass(self):
        with pytest.raises(errors.InvalidBassError):
            tokens.parse_colon_key_token("C::maj7/")

    def test_bad_slash_bass(self):
        with pytest.raises(errors.InvalidBassError):
            tokens.parse_colon_key_token("C::maj7/ZZ")

    def test_bad_repetition_count(self):
        with pytest.raises(errors.InvalidRepetitionError):
            tokens.parse_repetition_token("C*abc")

    def test_empty_repetition_base(self):
        with pytest.raises(errors.EmptyTokenError):
            tokens.parse_repetition_token("*3")

    def test_chain_without_bracket(self):
        with pytest.raises(errors.InvalidRepetitionError):
            tokens.parse_chain_repetition("C,G*2")

    def test_empty_chain(self):
        with pytest.raises(errors.EmptyTokenError):
            tokens.parse_chain_repetition("[]*2")

    def test_bad_duration_letter(self):
        with pytest.raises(errors.InvalidDurationError):
            percussion.parse_single_token("xk")

    def test_incomplete_perc_token(self):
        with pytest.raises(errors.InvalidDurationError):
            percussion.parse_single_token("q")

    def test_unknown_drum_letter(self):
        with pytest.raises(errors.InvalidDrumLetterError):
            percussion.parse_single_token("q!")

    def test_empty_perc_token(self):
        with pytest.raises(errors.EmptyTokenError):
            percussion.parse_single_token("   ")


class TestClassifyException:
    def test_typed_error_classifies_by_type_not_message(self):
        """Even with a message no regex matches, the type wins."""
        exc = errors.InvalidKeyError("completely reworded message")
        error_type, suggestion, code = api.classify_exception(exc)
        assert error_type == "invalid_chord"
        assert code == "ERR_CHORD_001"
        assert "note names" in suggestion

    def test_subclass_falls_back_up_the_mro(self):
        """A new subclass without its own registry entry inherits the
        nearest ancestor's suggestion (and its own class attributes)."""

        class CustomKeyError(errors.InvalidKeyError):
            pass

        error_type, suggestion, code = api.classify_exception(CustomKeyError("x"))
        assert error_type == "invalid_chord"
        assert code == "ERR_CHORD_001"
        assert suggestion

    def test_base_token_syntax_error_gets_generic_suggestion(self):
        error_type, _s, code = api.classify_exception(
            errors.TokenSyntaxError("Too many ':' sections in 'a:b:c:d'"))
        assert error_type == "invalid_syntax"
        assert code == "ERR_SYNTAX_000"

    def test_untyped_error_falls_back_to_message_matching(self):
        error_type, _s, code = api.classify_exception(ValueError("Bad key 'Q'"))
        assert error_type == "invalid_chord"
        assert code == "ERR_CHORD_001"

    def test_each_registered_type_maps_to_its_own_fields(self):
        cases = {
            errors.InvalidRecipeError: ("invalid_recipe", "ERR_CHORD_002"),
            errors.InvalidBassError: ("invalid_chord", "ERR_CHORD_003"),
            errors.InvalidDrumLetterError: ("invalid_drum", "ERR_PERC_001"),
            errors.InvalidDurationError: ("invalid_duration", "ERR_DUR_001"),
            errors.InvalidPresetError: ("invalid_preset", "ERR_PRESET_001"),
            errors.InvalidRepetitionError: ("invalid_syntax", "ERR_SYNTAX_001"),
            errors.EmptyTokenError: ("invalid_syntax", "ERR_SYNTAX_002"),
        }
        for klass, (etype, code) in cases.items():
            got_type, got_sugg, got_code = api.classify_exception(klass("msg"))
            assert got_type == etype, klass
            assert got_code == code, klass
            assert got_sugg, klass


class TestApiSurfacesTypedClassification:
    def test_generate_bad_key(self):
        with pytest.raises(api.GenerationError) as ei:
            api.generate({"keys": "ZZ", "seconds": 4})
        assert ei.value.error_type == "invalid_chord"
        assert ei.value.code == "ERR_CHORD_001"
        assert ei.value.suggestion

    def test_generate_unknown_preset(self):
        with pytest.raises(api.GenerationError) as ei:
            api.generate({"keys_preset": "no-such-preset", "seconds": 4})
        assert ei.value.error_type == "invalid_preset"
        assert ei.value.code == "ERR_PRESET_001"

    def test_parse_keys_uses_typed_classification(self):
        res = api.parse_keys("C, ZZ, G")
        assert not res["ok"]
        assert "note names" in res["suggestion"]

    def test_parse_perc_bad_letter_gets_drum_suggestion(self):
        res = api.parse_perc("qb, q!")
        assert not res["ok"]
        assert "drum letters" in res["suggestion"].lower()


class TestArgumentBounds:
    """The API boundary rejects non-positive / resource-abusive args as
    structured errors instead of rendering nonsense (found by fuzzing:
    seconds=-1.5 used to 'succeed' with a negative-duration result)."""

    def test_negative_seconds_rejected(self):
        with pytest.raises(api.GenerationError) as ei:
            api.generate({"keys": "C", "seconds": -1.5})
        assert ei.value.error_type == "invalid_argument"
        assert ei.value.code == "ERR_ARG_001"

    def test_zero_seconds_rejected(self):
        with pytest.raises(api.GenerationError):
            api.generate({"keys": "C", "seconds": 0})

    def test_huge_seconds_rejected(self):
        with pytest.raises(api.GenerationError) as ei:
            api.generate({"keys": "C", "seconds": 10**6})
        assert ei.value.code == "ERR_ARG_001"

    def test_absurd_bpm_rejected(self):
        with pytest.raises(api.GenerationError) as ei:
            api.generate({"keys": "C", "seconds": 4, "bpm": 12862})
        assert ei.value.error_type == "invalid_argument"
        assert ei.value.code == "ERR_ARG_002"

    def test_boundary_values_accepted(self):
        assert api.generate({"keys": "C", "seconds": 600, "bpm": 40,
                             "seed": 1}).duration_seconds == 600
        assert api.generate({"keys": "C", "seconds": 1, "bpm": 960,
                             "seed": 1}).midi
