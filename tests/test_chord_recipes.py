"""Pins library.chord_recipes.recipe_catalog(), which parses this module's own
source comments for the webapp's chord-recipe browser. A fragile regex parser
over hand-written comments — this guards against silent drift if the source
comments are ever restructured.
"""

from library.chord_recipes import CHORD_RECIPES, recipe_catalog


def test_recipe_catalog_covers_every_recipe():
    catalog = recipe_catalog()
    names = {r["name"] for r in catalog}
    assert names == set(CHORD_RECIPES)


def test_recipe_catalog_intervals_match_source():
    catalog = {r["name"]: r for r in recipe_catalog()}
    for name, intervals in CHORD_RECIPES.items():
        assert catalog[name]["intervals"] == intervals


def test_recipe_catalog_has_categories_and_notes():
    catalog = recipe_catalog()
    for r in catalog:
        assert r["category"]
        assert len(r["notes"]) == len(r["intervals"])
        assert all(n in {"C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"} for n in r["notes"])


def test_recipe_catalog_known_entries():
    catalog = {r["name"]: r for r in recipe_catalog()}
    assert catalog["maj"]["category"] == "Triads"
    assert catalog["maj"]["notes"] == ["C", "E", "G"]
    assert catalog["min7"]["description"] == "Minor 7"
