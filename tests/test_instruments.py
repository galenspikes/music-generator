"""Tests for the General MIDI instrument catalog (mtheory.GM_CATALOG) and the
extended resolve_instrument() — added for the webapp's instrument/soundfont
picker (docs/design-notes/ui-ux-roadmap.md Thread D). GM_ALIASES (the short,
curated CLI vocabulary) is untouched; this catalog is purely additive.
"""

import music_generator as M


def test_catalog_covers_all_128_gm_programs():
    assert len(M.GM_CATALOG) == 128
    assert [e["program"] for e in M.GM_CATALOG] == list(range(128))


def test_catalog_entries_are_well_formed():
    for e in M.GM_CATALOG:
        assert isinstance(e["name"], str) and e["name"]
        assert e["family"] in {name for name, _, _ in M.GM_FAMILIES}


def test_families_partition_all_128_programs_without_overlap():
    covered = []
    for _name, lo, hi in M.GM_FAMILIES:
        covered.extend(range(lo, hi))
    assert sorted(covered) == list(range(128))


def test_families_match_known_anchors():
    by_program = {e["program"]: e for e in M.GM_CATALOG}
    assert by_program[0]["name"] == "Acoustic Grand Piano"
    assert by_program[0]["family"] == "Piano"
    assert by_program[4]["name"] == "Electric Piano 1"
    assert by_program[32]["family"] == "Bass"
    assert by_program[40]["family"] == "Strings"
    assert by_program[127]["name"] == "Gunshot"
    assert by_program[127]["family"] == "Sound Effects"


def test_resolve_instrument_accepts_full_gm_names():
    assert M.resolve_instrument("Electric Piano 1") == 4
    assert M.resolve_instrument("electric piano 1") == 4  # case-insensitive
    assert M.resolve_instrument("Tenor Sax") == 66


def test_resolve_instrument_still_accepts_short_aliases_and_numbers():
    assert M.resolve_instrument("epiano") == 4
    assert M.resolve_instrument("42") == 42


def test_resolve_instrument_unknown_name_defaults_to_grand_piano():
    assert M.resolve_instrument("not-a-real-instrument") == 0
