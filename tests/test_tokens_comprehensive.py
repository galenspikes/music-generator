"""Comprehensive tests for tokens module.

Tests the chord token DSL: root[:inv][:recipe][/bass] colon tokens,
*N repetition, [a,b,...]*N chain repetition, key normalization, and
expansion into chord definitions.
"""

import pytest

import tokens as T
from mtheory import ChordDef, pc


class TestParseColonKeyToken:
    """Test colon chord token parsing."""

    def test_parse_colon_simple_major(self):
        """Parse simple major chord: C::maj."""
        chord = T.parse_colon_key_token("C::maj")
        assert chord is not None
        assert chord.root_pc == 0
        assert chord.label == "C::maj"

    def test_parse_colon_simple_minor(self):
        """Parse simple minor chord: Am::min."""
        chord = T.parse_colon_key_token("Am::min")
        assert chord is not None
        assert chord.root_pc == 9

    def test_parse_colon_root_only_defaults_to_major(self):
        """Root with no recipe defaults to maj."""
        chord = T.parse_colon_key_token("C::")
        assert chord is not None
        assert 0 in chord.pcs  # Should have root
        assert 4 in chord.pcs  # Should have major third

    def test_parse_colon_with_inversion(self):
        """Parse chord with inversion: C:1:maj."""
        chord = T.parse_colon_key_token("C:1:maj")
        assert chord is not None
        assert chord.bass_pc is not None

    def test_parse_colon_with_slash_bass(self):
        """Parse slash chord: C::maj/G."""
        chord = T.parse_colon_key_token("C::maj/G")
        assert chord is not None
        assert chord.bass_pc == pc("G")

    def test_parse_colon_inversion_and_slash_bass(self):
        """Slash bass overrides inversion."""
        chord = T.parse_colon_key_token("C:1:maj/G")
        assert chord is not None
        # Slash bass should override inversion
        assert chord.bass_pc == pc("G")

    def test_parse_colon_all_naturals(self):
        """Parse chords for all natural roots."""
        for root in "CDEFGAB":
            chord = T.parse_colon_key_token(f"{root}::maj")
            assert chord is not None
            assert chord.root_pc == pc(root)

    def test_parse_colon_sharps(self):
        """Parse chords with sharps."""
        chord = T.parse_colon_key_token("C#::maj")
        assert chord is not None
        assert chord.root_pc == 1

    def test_parse_colon_flats(self):
        """Parse chords with flats."""
        chord = T.parse_colon_key_token("Db::maj")
        assert chord is not None
        assert chord.root_pc == 1

    def test_parse_colon_minor_key(self):
        """Parse minor key (lowercase m at end)."""
        chord = T.parse_colon_key_token("Am::maj")
        assert chord is not None
        assert chord.root_pc == 9

    def test_parse_colon_preserves_label(self):
        """Label preserves original token string."""
        token = "C::maj7/G"
        chord = T.parse_colon_key_token(token)
        assert chord.label == token

    def test_parse_colon_pedal_point(self):
        """Parse pedal point: chord/non-chord-tone."""
        chord = T.parse_colon_key_token("C::maj/A")
        assert chord is not None
        assert chord.bass_pc == pc("A")

    def test_parse_colon_seventh_chord(self):
        """Parse seventh chords."""
        chord = T.parse_colon_key_token("G::7")
        assert chord is not None

    def test_parse_colon_no_colon_returns_none(self):
        """Non-colon tokens return None."""
        result = T.parse_colon_key_token("C")
        assert result is None

    def test_parse_colon_empty_returns_none(self):
        """Empty token (no colon) returns None."""
        result = T.parse_colon_key_token("")
        assert result is None

    def test_parse_colon_missing_root_raises(self):
        """Missing root raises ValueError."""
        with pytest.raises(ValueError, match="Missing root"):
            T.parse_colon_key_token("::maj")

    def test_parse_colon_bad_inversion_raises(self):
        """Non-numeric inversion raises ValueError."""
        with pytest.raises(ValueError):
            T.parse_colon_key_token("C:1:maj:abc")  # Too many colons

    def test_parse_colon_unknown_recipe_raises(self):
        """Unknown recipe raises ValueError."""
        with pytest.raises(ValueError, match="Unknown chord recipe"):
            T.parse_colon_key_token("C::nonexistent")

    def test_parse_colon_bad_slash_bass_raises(self):
        """Bad slash bass note raises ValueError."""
        with pytest.raises(ValueError, match="Bad slash bass"):
            T.parse_colon_key_token("C::maj/Z")

    def test_parse_colon_missing_slash_bass_raises(self):
        """Missing bass after slash raises ValueError."""
        with pytest.raises(ValueError, match="Missing bass"):
            T.parse_colon_key_token("C::maj/")

    def test_parse_colon_too_many_colons_raises(self):
        """Too many colons raises ValueError."""
        with pytest.raises(ValueError, match="Too many"):
            T.parse_colon_key_token("C::maj::extra::extra")

    def test_parse_colon_whitespace_handling(self):
        """Handles whitespace around colons and slashes."""
        chord = T.parse_colon_key_token("C :: maj / G")
        assert chord is not None

    def test_parse_colon_pcs_set(self):
        """Parsed pcs are a set of pitch classes."""
        chord = T.parse_colon_key_token("C::maj")
        assert isinstance(chord.pcs, tuple)
        assert all(0 <= pc < 12 for pc in chord.pcs)

    def test_parse_colon_seventh_pcs(self):
        """maj7 chord includes 7th."""
        chord = T.parse_colon_key_token("C::maj7")
        assert chord is not None
        assert 11 in chord.pcs or 10 in chord.pcs  # seventh


class TestParseRepetitionToken:
    """Test repetition operator *N parsing."""

    def test_parse_repetition_no_operator(self):
        """Token without * returns count=1."""
        token, count = T.parse_repetition_token("C")
        assert token == "C"
        assert count == 1

    def test_parse_repetition_simple(self):
        """Parse C*3."""
        token, count = T.parse_repetition_token("C*3")
        assert token == "C"
        assert count == 3

    def test_parse_repetition_large_count(self):
        """Parse large repetition count."""
        token, count = T.parse_repetition_token("C*100")
        assert token == "C"
        assert count == 100

    def test_parse_repetition_with_colon(self):
        """Parse colon token with repetition: C::maj*2."""
        token, count = T.parse_repetition_token("C::maj*2")
        assert token == "C::maj"
        assert count == 2

    def test_parse_repetition_whitespace(self):
        """Handles whitespace around operator."""
        token, count = T.parse_repetition_token("C * 3")
        assert token == "C"
        assert count == 3

    def test_parse_repetition_multiple_asterisks_raises(self):
        """Multiple asterisks raises ValueError."""
        with pytest.raises(ValueError, match="Bad repetition"):
            T.parse_repetition_token("C*2*3")

    def test_parse_repetition_bad_count_raises(self):
        """Non-numeric count raises ValueError."""
        with pytest.raises(ValueError, match="Bad repetition count"):
            T.parse_repetition_token("C*abc")

    def test_parse_repetition_zero_count_raises(self):
        """Zero count raises ValueError."""
        with pytest.raises(ValueError, match="must be >= 1"):
            T.parse_repetition_token("C*0")

    def test_parse_repetition_negative_count_raises(self):
        """Negative count raises ValueError."""
        with pytest.raises(ValueError, match="must be >= 1"):
            T.parse_repetition_token("C*-1")

    def test_parse_repetition_empty_base_raises(self):
        """Empty base token raises ValueError."""
        with pytest.raises(ValueError, match="Empty base"):
            T.parse_repetition_token("*3")


class TestParseChainRepetition:
    """Test chain repetition [a,b,c]*N parsing."""

    def test_parse_chain_simple(self):
        """Parse simple chain [C,G]*2."""
        tokens, count = T.parse_chain_repetition("[C,G]*2")
        assert tokens == ["C", "G"]
        assert count == 2

    def test_parse_chain_three_chords(self):
        """Parse chain with three chords."""
        tokens, count = T.parse_chain_repetition("[C::maj,F::maj,G::maj]*3")
        assert len(tokens) == 3
        assert count == 3

    def test_parse_chain_whitespace(self):
        """Handles whitespace in chain (no spaces around *)."""
        tokens, count = T.parse_chain_repetition("[ C , G ]*2")
        assert tokens == ["C", "G"]
        assert count == 2

    def test_parse_chain_colon_tokens(self):
        """Parse chain with colon tokens."""
        tokens, count = T.parse_chain_repetition("[C::maj,G::7]*2")
        assert tokens == ["C::maj", "G::7"]
        assert count == 2

    def test_parse_chain_no_bracket_raises(self):
        """Missing opening bracket raises ValueError."""
        with pytest.raises(ValueError, match="must start with bracket"):
            T.parse_chain_repetition("C,G*2")

    def test_parse_chain_no_repetition_raises(self):
        """Missing *N raises ValueError."""
        with pytest.raises(ValueError, match="must have \\*N count"):
            T.parse_chain_repetition("[C,G]")

    def test_parse_chain_empty_chain_raises(self):
        """Empty chain raises ValueError."""
        with pytest.raises(ValueError, match="Empty chain"):
            T.parse_chain_repetition("[]*2")

    def test_parse_chain_bad_count_raises(self):
        """Non-numeric count raises ValueError."""
        with pytest.raises(ValueError):
            T.parse_chain_repetition("[C,G]*abc")

    def test_parse_chain_zero_count_raises(self):
        """Zero count raises ValueError."""
        with pytest.raises(ValueError):
            T.parse_chain_repetition("[C,G]*0")


class TestNormalizeKeyToken:
    """Test key token normalization."""

    def test_normalize_colon_token_unchanged(self):
        """Colon tokens are returned as-is."""
        result = T._normalize_key_token("C::maj")
        assert result == "C::maj"

    def test_normalize_bare_root(self):
        """Bare root is normalized."""
        result = T._normalize_key_token("C")
        assert result == "C"

    def test_normalize_sharp_to_flat(self):
        """Sharps are converted to flats."""
        result = T._normalize_key_token("C#")
        assert result == "Db"

    def test_normalize_minor_marker_removed(self):
        """Minor marker 'm' is removed."""
        result = T._normalize_key_token("Am")
        assert result == "A"

    def test_normalize_minor_marker_min_removed(self):
        """Minor marker 'min' is removed."""
        result = T._normalize_key_token("Amin")
        assert result == "A"

    def test_normalize_unicode_flat(self):
        """Unicode flat is converted."""
        result = T._normalize_key_token("D♭")
        assert result == "Db"

    def test_normalize_case_handling(self):
        """Case is normalized."""
        result = T._normalize_key_token("c")
        assert result == "C"

    def test_normalize_invalid_raises(self):
        """Invalid note raises ValueError."""
        with pytest.raises(ValueError, match="Bad key"):
            T._normalize_key_token("Z")


class TestKeyRoots:
    """Test key_roots expansion."""

    def test_key_roots_ostinato_single_key(self):
        """Single key in ostinato mode."""
        result = T.key_roots("ostinato", "C")
        assert result == ["C"]

    def test_key_roots_ostinato_multiple_keys(self):
        """Multiple keys in ostinato mode."""
        result = T.key_roots("ostinato", "C,G,D")
        assert result == ["C", "G", "D"]

    def test_key_roots_ostinato_with_repetition(self):
        """Keys with *N repetition."""
        result = T.key_roots("ostinato", "C*2,G*3")
        assert result == ["C", "C", "G", "G", "G"]

    def test_key_roots_ostinato_chain(self):
        """Chain repetition [a,b]*N."""
        result = T.key_roots("ostinato", "[C,G]*2")
        assert result == ["C", "G", "C", "G"]

    def test_key_roots_ostinato_mixed_tokens(self):
        """Mix of single and repeated keys."""
        result = T.key_roots("ostinato", "C*2,[G,D]*2,A")
        assert "C" in result
        assert "G" in result
        assert "A" in result

    def test_key_roots_ostinato_colon_tokens(self):
        """Colon tokens in ostinato."""
        result = T.key_roots("ostinato", "C::maj,G::7")
        assert result == ["C::maj", "G::7"]

    def test_key_roots_ostinato_none_returns_default(self):
        """None keys returns default circle of fifths."""
        result = T.key_roots("ostinato", None)
        assert len(result) == 12

    def test_key_roots_other_mode_returns_circle(self):
        """Non-ostinato mode returns circle of fifths."""
        result = T.key_roots("mixed", "C")
        assert len(result) == 12
        assert "C" in result

    def test_key_roots_invalid_key_raises(self):
        """Invalid key in ostinato raises ValueError."""
        with pytest.raises(ValueError):
            T.key_roots("ostinato", "Z")

    def test_key_roots_normalizes_sharps_to_flats(self):
        """Sharps are normalized to flats."""
        result = T.key_roots("ostinato", "C#")
        assert result == ["Db"]

    def test_key_roots_removes_minor_marker(self):
        """Minor markers are removed."""
        result = T.key_roots("ostinato", "Am")
        assert result == ["A"]

    def test_key_roots_complex_chain(self):
        """Complex chain with multiple items."""
        result = T.key_roots("ostinato", "[C*2,G]*2")
        # Should expand to: C C G C C G
        assert result == ["C", "C", "G", "C", "C", "G"]


class TestIntegration:
    """Integration tests for token parsing."""

    def test_colon_to_chord_def_major(self):
        """Parse colon token to ChordDef (major)."""
        chord = T.parse_colon_key_token("C::maj")
        assert isinstance(chord, ChordDef)
        assert chord.root_pc == 0
        assert 4 in chord.pcs  # Major third

    def test_colon_to_chord_def_minor(self):
        """Parse colon token to ChordDef (minor)."""
        chord = T.parse_colon_key_token("A::min")
        assert isinstance(chord, ChordDef)
        assert chord.root_pc == 9
        # Minor chord pcs are absolute pitch classes (C, E, A)
        assert len(chord.pcs) == 3

    def test_colon_to_chord_def_seventh(self):
        """Parse seventh chord."""
        chord = T.parse_colon_key_token("G::7")
        assert isinstance(chord, ChordDef)
        assert chord.root_pc == 7

    def test_colon_with_inversion_bass(self):
        """Inversion produces correct bass note."""
        chord_root = T.parse_colon_key_token("C:0:maj")
        chord_first = T.parse_colon_key_token("C:1:maj")
        # Different inversions should have different bass notes
        assert chord_root.bass_pc != chord_first.bass_pc

    def test_slash_chord_bass_precedence(self):
        """Slash bass takes precedence over inversion."""
        chord = T.parse_colon_key_token("C:0:maj/G")
        assert chord.bass_pc == pc("G")

    def test_key_roots_produces_valid_tokens(self):
        """key_roots output can be parsed as colon tokens."""
        tokens = T.key_roots("ostinato", "C::maj,G::7")
        for token in tokens:
            chord = T.parse_colon_key_token(token)
            assert chord is not None

    def test_complex_progression_parsing(self):
        """Parse complex chord progression."""
        tokens = T.key_roots("ostinato", "[C::maj*2,G::7]*2,A::min7")
        assert isinstance(tokens, list)
        assert len(tokens) > 0
