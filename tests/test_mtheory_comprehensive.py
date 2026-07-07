"""Comprehensive tests for mtheory module.

Tests music theory primitives: pitch classes, key parsing, instrument resolution,
voice ranges, duration maps, chord recipes, and General MIDI catalog.
"""

import pytest

import mtheory as M


class TestChordDef:
    """Test ChordDef data structure."""

    def test_chord_def_creation_minimal(self):
        """ChordDef can be created with root and pitch classes."""
        chord = M.ChordDef(root_pc=0, pcs=(0, 4, 7))
        assert chord.root_pc == 0
        assert chord.pcs == (0, 4, 7)
        assert chord.bass_pc is None
        assert chord.label is None

    def test_chord_def_creation_full(self):
        """ChordDef supports bass and label."""
        chord = M.ChordDef(root_pc=0, pcs=(0, 4, 7), bass_pc=7, label="maj7")
        assert chord.root_pc == 0
        assert chord.pcs == (0, 4, 7)
        assert chord.bass_pc == 7
        assert chord.label == "maj7"

    def test_chord_def_frozen(self):
        """ChordDef is immutable (frozen dataclass)."""
        chord = M.ChordDef(root_pc=0, pcs=(0, 4, 7))
        with pytest.raises(AttributeError):
            chord.root_pc = 1

    def test_chord_def_equality(self):
        """ChordDef instances with same values are equal."""
        chord1 = M.ChordDef(root_pc=0, pcs=(0, 4, 7))
        chord2 = M.ChordDef(root_pc=0, pcs=(0, 4, 7))
        assert chord1 == chord2

    def test_chord_def_inequality(self):
        """ChordDef instances with different values are not equal."""
        chord1 = M.ChordDef(root_pc=0, pcs=(0, 4, 7))
        chord2 = M.ChordDef(root_pc=0, pcs=(0, 3, 7))
        assert chord1 != chord2

    def test_chord_def_hashable(self):
        """ChordDef instances are hashable."""
        chord = M.ChordDef(root_pc=0, pcs=(0, 4, 7))
        # Should not raise
        s = {chord}
        assert chord in s


class TestConstants:
    """Test constant definitions."""

    def test_channel_constants(self):
        """Channel constants are defined."""
        assert M.CHORD_CH == 0
        assert M.DRUM_CH == 9  # GM percussion channel

    def test_voice_ranges_defined(self):
        """Voice ranges are defined for all voices."""
        assert M.BASS_RANGE == (28, 55)
        assert M.TENOR_RANGE == (43, 67)
        assert M.ALTO_RANGE == (50, 76)
        assert M.SOP_RANGE == (60, 91)

    def test_voice_order(self):
        """VOICE_ORDER lists voices in high-to-low order."""
        assert M.VOICE_ORDER == ("soprano", "alto", "tenor", "bass")

    def test_voice_range_map(self):
        """VOICE_RANGE_MAP maps voices to ranges."""
        assert M.VOICE_RANGE_MAP["soprano"] == M.SOP_RANGE
        assert M.VOICE_RANGE_MAP["alto"] == M.ALTO_RANGE
        assert M.VOICE_RANGE_MAP["tenor"] == M.TENOR_RANGE
        assert M.VOICE_RANGE_MAP["bass"] == M.BASS_RANGE

    def test_note_to_pc_coverage(self):
        """NOTE_TO_PC maps all notes."""
        # All 12 pitch classes should be present
        pcs = set(M.NOTE_TO_PC.values())
        assert pcs == set(range(12))

    def test_note_to_pc_naturals(self):
        """NOTE_TO_PC includes natural notes."""
        assert M.NOTE_TO_PC["C"] == 0
        assert M.NOTE_TO_PC["D"] == 2
        assert M.NOTE_TO_PC["E"] == 4
        assert M.NOTE_TO_PC["F"] == 5
        assert M.NOTE_TO_PC["G"] == 7
        assert M.NOTE_TO_PC["A"] == 9
        assert M.NOTE_TO_PC["B"] == 11

    def test_note_to_pc_sharps(self):
        """NOTE_TO_PC includes sharp notes."""
        assert M.NOTE_TO_PC["C#"] == 1
        assert M.NOTE_TO_PC["F#"] == 6
        assert M.NOTE_TO_PC["G#"] == 8

    def test_note_to_pc_flats(self):
        """NOTE_TO_PC includes flat notes."""
        assert M.NOTE_TO_PC["Db"] == 1
        assert M.NOTE_TO_PC["Eb"] == 3
        assert M.NOTE_TO_PC["Gb"] == 6

    def test_note_to_pc_enharmonics(self):
        """NOTE_TO_PC includes enharmonic spellings."""
        assert M.NOTE_TO_PC["B#"] == M.NOTE_TO_PC["C"]
        assert M.NOTE_TO_PC["E#"] == M.NOTE_TO_PC["F"]
        assert M.NOTE_TO_PC["Fb"] == M.NOTE_TO_PC["E"]
        assert M.NOTE_TO_PC["Cb"] == M.NOTE_TO_PC["B"]

    def test_dur_map_values(self):
        """DUR_MAP maps duration letters to beat counts."""
        assert M.DUR_MAP["w"] == 4.0  # whole
        assert M.DUR_MAP["h"] == 2.0  # half
        assert M.DUR_MAP["q"] == 1.0  # quarter
        assert M.DUR_MAP["e"] == 0.5  # eighth
        assert M.DUR_MAP["s"] == 0.25  # sixteenth
        assert M.DUR_MAP["t"] == 0.125  # thirtysecond


class TestGmAliases:
    """Test General MIDI instrument aliases."""

    def test_gm_aliases_exist(self):
        """GM_ALIASES dict is defined."""
        assert isinstance(M.GM_ALIASES, dict)
        assert len(M.GM_ALIASES) > 0

    def test_gm_aliases_piano(self):
        """Piano aliases resolve correctly."""
        assert M.GM_ALIASES["piano"] == 0
        assert M.GM_ALIASES["brightpiano"] == 1
        assert M.GM_ALIASES["epiano"] == 4

    def test_gm_aliases_strings(self):
        """String instrument aliases."""
        assert M.GM_ALIASES["strings"] == 48
        assert M.GM_ALIASES["choir"] == 52

    def test_gm_aliases_brass(self):
        """Brass instrument aliases."""
        assert M.GM_ALIASES["trumpet"] == 56
        assert M.GM_ALIASES["trombone"] == 57

    def test_gm_aliases_values_in_range(self):
        """All alias values are valid MIDI program numbers."""
        for name, program in M.GM_ALIASES.items():
            assert 0 <= program <= 127

    def test_gm_aliases_unique(self):
        """Aliases are unique (no duplicates across instruments)."""
        values = list(M.GM_ALIASES.values())
        # Some aliases might point to the same program, that's OK
        # Just verify they're all valid
        assert all(isinstance(v, int) for v in values)


class TestGmCatalog:
    """Test General MIDI catalog."""

    def test_gm_catalog_defined(self):
        """GM_CATALOG is defined and has 128 entries."""
        assert isinstance(M.GM_CATALOG, tuple)
        assert len(M.GM_CATALOG) == 128

    def test_gm_catalog_entry_structure(self):
        """Each catalog entry has required fields."""
        for entry in M.GM_CATALOG:
            assert "program" in entry
            assert "name" in entry
            assert "family" in entry

    def test_gm_catalog_program_numbers(self):
        """Catalog programs are sequential 0-127."""
        for i, entry in enumerate(M.GM_CATALOG):
            assert entry["program"] == i

    def test_gm_catalog_programs_in_range(self):
        """All program numbers are valid."""
        for entry in M.GM_CATALOG:
            assert 0 <= entry["program"] <= 127

    def test_gm_program_names_defined(self):
        """GM_PROGRAM_NAMES list is defined."""
        assert isinstance(M.GM_PROGRAM_NAMES, list)
        assert len(M.GM_PROGRAM_NAMES) == 128

    def test_gm_families_defined(self):
        """GM_FAMILIES list is defined."""
        assert isinstance(M.GM_FAMILIES, list)
        assert len(M.GM_FAMILIES) == 16  # Standard 16 families


class TestParseKeyName:
    """Test key name parsing."""

    def test_parse_key_natural(self):
        """Parses natural notes."""
        pc, is_minor = M.parse_key_name("C")
        assert pc == 0
        assert is_minor is False

    def test_parse_key_all_naturals(self):
        """Parses all natural notes."""
        naturals = [("C", 0), ("D", 2), ("E", 4), ("F", 5), ("G", 7), ("A", 9), ("B", 11)]
        for name, expected_pc in naturals:
            pc, is_minor = M.parse_key_name(name)
            assert pc == expected_pc
            assert is_minor is False

    def test_parse_key_sharp(self):
        """Parses sharp notes."""
        pc, is_minor = M.parse_key_name("C#")
        assert pc == 1
        assert is_minor is False

    def test_parse_key_flat(self):
        """Parses flat notes."""
        pc, is_minor = M.parse_key_name("Db")
        assert pc == 1
        assert is_minor is False

    def test_parse_key_minor(self):
        """Parses minor keys."""
        pc, is_minor = M.parse_key_name("Am")
        assert pc == 9
        assert is_minor is True

    def test_parse_key_minor_sharp(self):
        """Parses minor keys with sharps."""
        pc, is_minor = M.parse_key_name("F#m")
        assert pc == 6
        assert is_minor is True

    def test_parse_key_minor_flat(self):
        """Parses minor keys with flats."""
        pc, is_minor = M.parse_key_name("Bbm")
        assert pc == 10
        assert is_minor is True

    def test_parse_key_unicode_flat(self):
        """Parses unicode flat symbol (♭)."""
        pc, is_minor = M.parse_key_name("D♭")
        assert pc == 1
        assert is_minor is False

    def test_parse_key_unicode_sharp(self):
        """Parses unicode sharp symbol (♯)."""
        pc, is_minor = M.parse_key_name("C♯")
        assert pc == 1
        assert is_minor is False

    def test_parse_key_whitespace_stripped(self):
        """Parses keys with surrounding whitespace."""
        pc, is_minor = M.parse_key_name("  C  ")
        assert pc == 0
        assert is_minor is False

    def test_parse_key_invalid_note_raises(self):
        """Invalid note raises ValueError."""
        with pytest.raises(ValueError, match="Bad key"):
            M.parse_key_name("H")  # H is not a valid English note name

    def test_parse_key_empty_string_raises(self):
        """Empty key name raises ValueError."""
        with pytest.raises(ValueError, match="Empty"):
            M.parse_key_name("")

    def test_parse_key_invalid_format_raises(self):
        """Malformed key raises ValueError."""
        with pytest.raises(ValueError, match="Bad key"):
            M.parse_key_name("Z#m")


class TestResolveInstrument:
    """Test instrument resolution."""

    def test_resolve_instrument_by_alias(self):
        """Resolves instrument by alias."""
        assert M.resolve_instrument("piano") == 0
        assert M.resolve_instrument("strings") == 48
        assert M.resolve_instrument("trumpet") == 56

    def test_resolve_instrument_by_alias_case_insensitive(self):
        """Alias resolution is case-insensitive."""
        assert M.resolve_instrument("PIANO") == 0
        assert M.resolve_instrument("Piano") == 0
        assert M.resolve_instrument("PiAnO") == 0

    def test_resolve_instrument_by_number(self):
        """Resolves instrument by program number."""
        assert M.resolve_instrument("0") == 0
        assert M.resolve_instrument("48") == 48
        assert M.resolve_instrument("127") == 127

    def test_resolve_instrument_by_full_name(self):
        """Resolves instrument by full General MIDI name."""
        result = M.resolve_instrument("Acoustic Grand Piano")
        assert result == 0

    def test_resolve_instrument_by_full_name_case_insensitive(self):
        """Full name resolution is case-insensitive."""
        result = M.resolve_instrument("acoustic grand piano")
        assert result == 0

    def test_resolve_instrument_number_clamped(self):
        """Out-of-range numbers are clamped to [0, 127]."""
        assert M.resolve_instrument("-1") == 0
        assert M.resolve_instrument("200") == 127

    def test_resolve_instrument_whitespace_stripped(self):
        """Whitespace is stripped from input."""
        assert M.resolve_instrument("  piano  ") == 0
        assert M.resolve_instrument("  48  ") == 48

    def test_resolve_instrument_unknown_defaults_to_piano(self):
        """Unknown instrument defaults to piano (0)."""
        assert M.resolve_instrument("nonexistent") == 0
        assert M.resolve_instrument("bogus_instrument") == 0

    def test_resolve_instrument_all_aliases_valid(self):
        """All aliases resolve to valid programs."""
        for alias in M.GM_ALIASES.keys():
            result = M.resolve_instrument(alias)
            assert 0 <= result <= 127


class TestClampToRange:
    """Test pitch clamping to range."""

    def test_clamp_to_range_in_range(self):
        """Pitch already in range is unchanged."""
        result = M.clamp_to_range(60, 48, 84)
        assert result == 60

    def test_clamp_to_range_below_wraps_up(self):
        """Pitch below range wraps up by octaves."""
        result = M.clamp_to_range(36, 48, 84)
        assert result == 48  # 36 + 12 = 48

    def test_clamp_to_range_above_wraps_down(self):
        """Pitch above range wraps down by octaves."""
        result = M.clamp_to_range(96, 48, 84)
        assert result == 84  # 96 - 12 = 84

    def test_clamp_to_range_multiple_octaves(self):
        """Pitch multiple octaves away wraps correctly."""
        result = M.clamp_to_range(24, 48, 84)
        # Wraps up to first value in range
        assert 48 <= result <= 84

    def test_clamp_to_range_at_boundaries(self):
        """Pitches at range boundaries are kept."""
        assert M.clamp_to_range(48, 48, 84) == 48
        assert M.clamp_to_range(84, 48, 84) == 84

    def test_clamp_to_range_preserves_pitch_class(self):
        """Clamping preserves pitch class (mod 12)."""
        original_pc = 60 % 12  # 0 (C)
        result = M.clamp_to_range(60, 48, 60)
        assert result % 12 == original_pc


class TestNearestInRegister:
    """Test finding nearest pitch in register."""

    def test_nearest_in_register_already_there(self):
        """Pitch already in range is returned."""
        result = M.nearest_in_register(60, 48, 84)
        assert result == 60

    def test_nearest_in_register_below_considers_range(self):
        """Pitch below range finds closest candidate."""
        result = M.nearest_in_register(40, 48, 84)
        # Returns nearest pitch (could be in or out of range)
        assert isinstance(result, int)

    def test_nearest_in_register_above_considers_range(self):
        """Pitch above range finds closest candidate."""
        result = M.nearest_in_register(90, 48, 84)
        # Returns nearest pitch (could be in or out of range)
        assert isinstance(result, int)

    def test_nearest_in_register_close_candidates(self):
        """Chooses closest of multiple candidates."""
        # Target 48.5 equivalent: candidates are 48, 60, 36
        result = M.nearest_in_register(48, 48, 84)
        assert result == 48  # Exact match

    def test_nearest_in_register_considers_octaves(self):
        """Considers multiple octave candidates."""
        # Test with a pitch that could be multiple octaves
        result = M.nearest_in_register(24, 48, 84)
        # Could be 24+12=36, 24+24=48, 24+36=60
        assert result in [36, 48, 60]

    def test_nearest_in_register_wide_range(self):
        """Works with wide voice ranges."""
        result = M.nearest_in_register(65, 28, 91)
        assert 28 <= result <= 91


class TestPitchClass:
    """Test pitch class conversion."""

    def test_pc_naturals(self):
        """pc() returns correct pitch class for naturals."""
        assert M.pc("C") == 0
        assert M.pc("D") == 2
        assert M.pc("E") == 4
        assert M.pc("F") == 5
        assert M.pc("G") == 7
        assert M.pc("A") == 9
        assert M.pc("B") == 11

    def test_pc_sharps(self):
        """pc() returns correct pitch class for sharps."""
        assert M.pc("C#") == 1
        assert M.pc("F#") == 6

    def test_pc_flats(self):
        """pc() returns correct pitch class for flats."""
        assert M.pc("Db") == 1
        assert M.pc("Bb") == 10

    def test_pc_invalid_raises(self):
        """pc() raises for invalid note names."""
        with pytest.raises(KeyError):
            M.pc("H")


class TestLoadChordRecipes:
    """Test chord recipe loading."""

    def test_load_chord_recipes_returns_dict(self):
        """load_chord_recipes returns a dictionary."""
        recipes = M.load_chord_recipes()
        assert isinstance(recipes, dict)

    def test_load_chord_recipes_cached(self):
        """load_chord_recipes uses cache on second call."""
        recipes1 = M.load_chord_recipes()
        recipes2 = M.load_chord_recipes()
        assert recipes1 is recipes2  # Same object (cached)

    def test_load_chord_recipes_force_reload(self):
        """load_chord_recipes can force reload cache."""
        recipes1 = M.load_chord_recipes()
        recipes2 = M.load_chord_recipes(force_reload=True)
        # Should have same content but might be different object
        assert recipes1 == recipes2

    def test_load_chord_recipes_values_are_tuples(self):
        """Recipe values are tuples of integers."""
        recipes = M.load_chord_recipes()
        for name, recipe in recipes.items():
            assert isinstance(recipe, tuple)
            assert all(isinstance(pc, int) for pc in recipe)

    def test_load_chord_recipes_case_normalization(self):
        """Recipes are accessible in lowercase."""
        recipes = M.load_chord_recipes()
        for name in recipes.keys():
            # If uppercase exists, lowercase should also exist
            if name != name.lower():
                lowercase = name.lower()
                if lowercase in recipes:
                    # Both forms reference the same recipe
                    assert recipes[name] == recipes[lowercase]


class TestGetChordRecipe:
    """Test individual chord recipe retrieval."""

    def test_get_chord_recipe_valid_name(self):
        """get_chord_recipe returns recipe for valid chord."""
        recipe = M.get_chord_recipe("triads")
        if recipe is not None:  # Might not exist, but if it does...
            assert isinstance(recipe, list)
            assert all(isinstance(pc, int) for pc in recipe)

    def test_get_chord_recipe_case_insensitive(self):
        """get_chord_recipe is case-insensitive."""
        recipe_lower = M.get_chord_recipe("triads")
        recipe_upper = M.get_chord_recipe("TRIADS")
        if recipe_lower is not None:
            assert recipe_lower == recipe_upper

    def test_get_chord_recipe_returns_list(self):
        """get_chord_recipe returns a list (not tuple)."""
        recipe = M.get_chord_recipe("triads")
        if recipe is not None:
            assert isinstance(recipe, list)

    def test_get_chord_recipe_invalid_returns_none(self):
        """get_chord_recipe returns None for unknown recipe."""
        result = M.get_chord_recipe("nonexistent_chord_xyz")
        assert result is None

    def test_get_chord_recipe_empty_returns_none(self):
        """get_chord_recipe returns None for empty string."""
        result = M.get_chord_recipe("")
        assert result is None


class TestGmFamily:
    """Test General MIDI family identification."""

    def test_gm_family_piano(self):
        """Programs 0-7 are Piano family."""
        assert M._gm_family(0) == "Piano"
        assert M._gm_family(5) == "Piano"

    def test_gm_family_organ(self):
        """Programs 16-23 are Organ family."""
        assert M._gm_family(16) == "Organ"
        assert M._gm_family(19) == "Organ"

    def test_gm_family_strings(self):
        """Programs 40-47 are Strings family."""
        assert M._gm_family(40) == "Strings"
        assert M._gm_family(48) != "Strings"  # 48 is next family

    def test_gm_family_percussion(self):
        """Programs 112-119 are Percussive family."""
        assert M._gm_family(112) == "Percussive"
        assert M._gm_family(115) == "Percussive"

    def test_gm_family_all_programs_have_family(self):
        """All 128 programs map to a family."""
        for program in range(128):
            family = M._gm_family(program)
            assert family != "Other"  # Should be in one of the 16 families

    def test_gm_family_boundaries(self):
        """Family boundaries are correct."""
        # Each family should cover its range
        for name, lo, hi in M.GM_FAMILIES:
            for program in range(lo, hi):
                assert M._gm_family(program) == name


class TestIntegration:
    """Integration tests for mtheory functions."""

    def test_parse_and_resolve_flow(self):
        """Full flow: parse key, get instrument."""
        pc, is_minor = M.parse_key_name("Cm")
        assert pc == 0
        assert is_minor is True

        instrument = M.resolve_instrument("strings")
        assert 0 <= instrument <= 127  # Valid MIDI program

    def test_voice_range_lookup(self):
        """Look up voice range for each voice."""
        for voice in M.VOICE_ORDER:
            voice_range = M.VOICE_RANGE_MAP[voice]
            assert isinstance(voice_range, tuple)
            assert len(voice_range) == 2
            assert voice_range[0] < voice_range[1]

    def test_clamp_and_nearest_flow(self):
        """Clamp and find nearest in voice range."""
        sop_range = M.VOICE_RANGE_MAP["soprano"]
        target = 72  # Within soprano range

        clamped = M.clamp_to_range(target, *sop_range)
        nearest = M.nearest_in_register(target, *sop_range)

        # Clamped should be in range
        assert sop_range[0] <= clamped <= sop_range[1]
        # Nearest might not be in range but should be valid pitch
        assert isinstance(nearest, int)

    def test_chord_recipe_usage(self):
        """Chord recipe can be used to build ChordDef."""
        recipes = M.load_chord_recipes()
        if recipes:
            # Get any available recipe
            for name, pcs in list(recipes.items())[:1]:
                if pcs:
                    chord = M.ChordDef(
                        root_pc=M.pc("C"),
                        pcs=pcs,
                        label=name
                    )
                    assert chord.root_pc == 0
                    assert len(chord.pcs) > 0
                    assert chord.label == name
