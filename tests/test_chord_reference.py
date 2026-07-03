"""The chord-reference generator: every recipe categorised, analysed, cited."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "library"))

import chord_reference as cr
from chord_recipes import CHORD_RECIPES


def test_build_catalog_covers_every_recipe_once():
    cat = cr.build_catalog()
    assert set(cat["recipes"]) == set(CHORD_RECIPES)
    listed = [n for c in cat["categories"] for n in c["names"]]
    assert sorted(listed) == sorted(CHORD_RECIPES)   # exactly once each


def test_every_recipe_is_categorised_and_named():
    cat = cr.build_catalog()["recipes"]
    for name, r in cat.items():
        assert r["category"], name
        assert r["forte"] and r["forte"] != "—", name  # all catalogue sets named
        assert r["prime"].startswith("["), name


def test_aliases_are_symmetric_for_identical_offsets():
    cat = cr.build_catalog()["recipes"]
    # m7b5 and hdim7 share [0,3,6,10]
    assert "hdim7" in cat["m7b5"]["aliases"]
    assert "m7b5" in cat["hdim7"]["aliases"]


def test_every_recipe_has_a_description_and_consonance():
    cat = cr.build_catalog()["recipes"]
    for name, r in cat.items():
        assert r["description"].strip(), name
        assert r["consonance"]["band"] in (
            "consonant", "mild", "tense", "dissonant", "harsh"), name
    # a plain (non-iconic) chord still gets a composed description
    assert "dyads are" in cat["min7"]["description"]
    # iconic chords append their cited note to the auto description
    assert 'href="#ref-' in cat["mystic"]["description"]


def test_iconic_chords_have_curated_notes_with_citations():
    cat = cr.build_catalog()["recipes"]
    for name in ("tristan", "mystic", "petrushka", "whole_tone"):
        assert cat[name]["curated"], name
        assert 'href="#ref-' in cat[name]["curated"], name  # footnote marker


def test_markdown_has_a_footnoted_bibliography():
    md = cr.render_markdown(cr.build_catalog())
    assert "## References" in md
    assert "[^forte]:" in md and "[^rahn]:" in md
    assert "| `maj7` |" in md


def test_html_is_self_contained_and_cites_sources():
    html = cr.render_html(cr.build_catalog(), full_document=True)
    assert "<!DOCTYPE html>" in html
    assert "<script src=" not in html          # no external script tags
    assert "cdn.jsdelivr" not in html
    assert 'id="ref-1"' in html and "Forte" in html


def test_artifact_body_has_no_document_scaffolding():
    body = cr.render_html(cr.build_catalog(), full_document=False)
    assert "<!DOCTYPE" not in body and "<head>" not in body
    assert "<style>" in body and 'id="chd-data"' in body
