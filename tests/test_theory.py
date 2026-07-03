"""Pitch-class set analysis (theory.py).

Prime forms and interval-class vectors are checked against hand-verified values;
Forte numbers are pinned to well-known anchors (Forte 1973) so a typo in the
table can't ship silently. Also asserts every catalogue recipe resolves to a
named set class.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "library"))

import theory as T
from chord_recipes import CHORD_RECIPES


def _pcs(name):
    return T.pitch_classes(CHORD_RECIPES[name])


# --- prime form / normal form -------------------------------------------------

def test_prime_forms_of_common_chords():
    cases = {
        "maj": [0, 3, 7], "min": [0, 3, 7], "dim": [0, 3, 6], "aug": [0, 4, 8],
        "maj7": [0, 1, 5, 8], "7": [0, 2, 5, 8], "min7": [0, 3, 5, 8],
        "dim7": [0, 3, 6, 9], "quartal": [0, 2, 7], "mystic": [0, 1, 3, 5, 7, 9],
        "whole_tone": [0, 2, 4, 6, 8, 10], "7alt": [0, 1, 3, 4, 6, 8, 10],
    }
    for name, pf in cases.items():
        assert T.prime_form(T.pitch_classes(CHORD_RECIPES[name])) == pf, name


def test_prime_form_is_transposition_and_inversion_invariant():
    base = [0, 4, 7, 11]  # maj7
    up = [(p + 5) % 12 for p in base]
    inv = [(-p) % 12 for p in base]
    assert T.prime_form(base) == T.prime_form(up) == T.prime_form(inv)


def test_set_class_table_prime_forms_are_self_consistent():
    # every key in the table must itself be a prime form
    for pf in T.SET_CLASSES:
        assert T.prime_form(list(pf)) == list(pf), pf


# --- interval-class vectors ---------------------------------------------------

def test_interval_class_vectors():
    def icv(n):
        return T.interval_class_vector(_pcs(n))
    assert icv("maj") == [0, 0, 1, 1, 1, 0]        # major triad
    assert icv("dim7") == [0, 0, 4, 0, 0, 2]       # fully diminished 7th
    assert icv("whole_tone") == [0, 6, 0, 6, 0, 3]  # whole-tone hexachord
    assert icv("mystic") == [1, 4, 2, 4, 2, 2]     # Scriabin mystic
    assert icv("7alt") == [2, 5, 4, 4, 4, 2]       # altered collection


# --- Forte numbers (anchors from Forte 1973) ----------------------------------

def test_forte_number_anchors():
    def fn(n):
        return T.forte_number(_pcs(n))
    anchors = {
        "maj": "3-11", "min": "3-11", "dim": "3-10", "aug": "3-12",
        "quartal": "3-9", "7": "4-27", "hdim7": "4-27", "min7": "4-26",
        "maj7": "4-20", "dim7": "4-28", "7#5": "4-24", "fr6": "4-25",
        "mmaj7": "4-19", "9": "5-34", "so_what": "5-35",
        "mystic": "6-34", "whole_tone": "6-35", "7alt": "7-34",
    }
    for name, forte in anchors.items():
        assert fn(name) == forte, f"{name}: got {fn(name)}, want {forte}"


def test_every_recipe_has_a_named_set_class():
    missing = [n for n, offs in CHORD_RECIPES.items()
               if T.forte_number(T.pitch_classes(offs)) is None]
    assert missing == [], f"unnamed set classes: {missing}"


# --- symmetry / character -----------------------------------------------------

def test_transpositional_symmetry():
    def sym(n):
        return T.transpositional_symmetry(_pcs(n))
    assert sym("whole_tone") == 5   # maps to itself at every even transposition
    assert sym("dim7") == 3         # T3/T6/T9
    assert sym("aug") == 2          # T4/T8
    assert sym("maj7") == 0         # asymmetric


def test_inversional_and_quartal_flags():
    assert "inversionally symmetric" in T.character_flags(CHORD_RECIPES["dim7"])
    assert "quartal / quintal" in T.character_flags(CHORD_RECIPES["quartal"])
    assert "quartal / quintal" in T.character_flags(CHORD_RECIPES["so_what"])
    assert "whole-tone subset" in T.character_flags(CHORD_RECIPES["whole_tone"])
    # the two all-interval tetrachords in the catalogue: ger6 (4-Z15), majadd#11 (4-Z29)
    assert "all-interval tetrachord" in T.character_flags(CHORD_RECIPES["ger6"])
    assert "all-interval tetrachord" in T.character_flags(CHORD_RECIPES["majadd#11"])


# --- spelling / analysis record ----------------------------------------------

def test_analyze_spells_notes_over_the_root():
    a = T.analyze(CHORD_RECIPES["maj7"], root_pc=0, root_letter="C")
    assert [n["name"] for n in a["notes"]] == ["C", "E", "G", "B"]
    assert [n["degree"] for n in a["notes"]] == ["R", "3", "5", "7"]
    assert a["prime_str"] == "[0 1 5 8]"
    assert a["forte"] == "4-20"


def test_analyze_uses_flats_for_minor_degrees():
    a = T.analyze(CHORD_RECIPES["min7"], root_pc=0, root_letter="C")
    assert [n["name"] for n in a["notes"]] == ["C", "E♭", "G", "B♭"]


def test_stacked_intervals_of_a_seventh_chord():
    assert T.stacked_intervals(CHORD_RECIPES["maj7"]) == ["M3", "m3", "M3"]


# --- consonance / dissonance (Huron 1994) -------------------------------------

def test_consonance_bands_and_ordering():
    def con(n):
        return T.consonance(_pcs(n))
    assert con("maj")["band"] == "consonant"
    assert con("quartal")["band"] == "consonant"      # fourths score high
    assert con("tone_cluster_3")["band"] == "harsh"
    # more clash => higher dissonance index
    order = ["maj", "7", "7b9", "tone_cluster_3"]
    idx = [con(n)["index"] for n in order]
    assert idx == sorted(idx), idx
    assert all(0.0 <= v <= 1.0 for v in idx)


def test_consonance_reading_names_the_sharp_intervals():
    assert T.consonance(_pcs("maj"))["reading"] == "no semitones or tritones"
    r = T.consonance(_pcs("7"))["reading"]           # dominant 7th: one tritone
    assert "1 tritone" in r
