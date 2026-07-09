# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""Typed exceptions for the token DSLs (chords, percussion, presets).

Every class subclasses :class:`ValueError`, so existing ``except ValueError``
call sites keep working — the types only *add* information. Each class carries
a machine-readable ``error_type`` and ``code`` so the API boundary
(:mod:`generator_api`) can classify an error by ``isinstance`` dispatch
instead of pattern-matching the human message string (which was brittle:
rewording a message silently broke its classification).

The user-facing *suggestion* text is deliberately not defined here: good
suggestions need runtime context (the active drum map, the recipe catalog)
that belongs to the API layer. See ``generator_api._EXC_SUGGESTIONS``.

This module has no imports, so every layer (mtheory, tokens, percussion,
arrangement, generator_api) can raise these without dependency cycles.
"""

__all__ = [
    "TokenSyntaxError",
    "InvalidKeyError",
    "InvalidRecipeError",
    "InvalidBassError",
    "InvalidDrumLetterError",
    "InvalidDurationError",
    "InvalidPresetError",
    "InvalidRepetitionError",
    "EmptyTokenError",
]


class TokenSyntaxError(ValueError):
    """Base for all DSL parse errors. ``error_type``/``code`` classify the
    error for API consumers; subclasses override them."""

    error_type = "invalid_syntax"
    code = "ERR_SYNTAX_000"


class InvalidKeyError(TokenSyntaxError):
    """A chord root / key name that isn't a note name (``Bad key 'ZZ'``)."""

    error_type = "invalid_chord"
    code = "ERR_CHORD_001"


class InvalidRecipeError(TokenSyntaxError):
    """An unknown chord recipe name, or a recipe with no tones."""

    error_type = "invalid_recipe"
    code = "ERR_CHORD_002"


class InvalidBassError(TokenSyntaxError):
    """A slash chord with a missing or unparseable bass note."""

    error_type = "invalid_chord"
    code = "ERR_CHORD_003"


class InvalidDrumLetterError(TokenSyntaxError):
    """A percussion letter not present in the active drum map."""

    error_type = "invalid_drum"
    code = "ERR_PERC_001"


class InvalidDurationError(TokenSyntaxError):
    """A rhythm token whose duration letter is missing or unknown."""

    error_type = "invalid_duration"
    code = "ERR_DUR_001"


class InvalidPresetError(TokenSyntaxError):
    """An unknown keys-preset name."""

    error_type = "invalid_preset"
    code = "ERR_PRESET_001"


class InvalidRepetitionError(TokenSyntaxError):
    """Malformed ``*N`` repetition or ``[...]*N`` chain syntax."""

    error_type = "invalid_syntax"
    code = "ERR_SYNTAX_001"


class EmptyTokenError(TokenSyntaxError):
    """A token that came out empty (stray comma, dangling ``:`` …)."""

    error_type = "invalid_syntax"
    code = "ERR_SYNTAX_002"
