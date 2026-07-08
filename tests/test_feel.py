"""Tests for genre feel presets (feel.py + arrangement wiring, Thread 3 v3)."""

import pytest

import arrangement as A
import feel


def test_expand_feel_known_names():
    for name in feel.list_feels():
        overlay = feel.expand_feel(name)
        assert isinstance(overlay, dict)


def test_expand_feel_unknown_name_errors():
    with pytest.raises(ValueError):
        feel.expand_feel("bogus")


def test_expand_feel_is_case_insensitive():
    assert feel.expand_feel("FUNK") == feel.expand_feel("funk")


def test_expand_feel_returns_a_copy():
    overlay = feel.expand_feel("funk")
    overlay["perc"]["ghost_rate"] = 999
    assert feel.FEEL_PRESETS["funk"]["perc"]["ghost_rate"] != 999


def test_presets_only_use_known_section_keys():
    # every overlay key must exist in the arrangement's defaults schema, so a
    # feel can never introduce config the engine doesn't read
    for name in feel.list_feels():
        for key, val in feel.expand_feel(name).items():
            assert key in A.BASE_DEFAULTS, (name, key)
            if isinstance(val, dict):
                assert isinstance(A.BASE_DEFAULTS[key], dict), (name, key)
                for sub in val:
                    assert sub in A.BASE_DEFAULTS[key], (name, key, sub)


def test_preset_values_in_sane_ranges():
    for name in feel.list_feels():
        overlay = feel.expand_feel(name)
        assert 0.0 <= overlay.get("swing", 0.0) <= 0.75
        perc = overlay.get("perc", {})
        assert 0.0 <= perc.get("ghost_rate", 0.0) <= 1.0
        for delay in perc.get("pocket", {}).values():
            assert 0.0 <= delay <= 0.1  # pocket, not sloppiness


# --- arrangement wiring ------------------------------------------------------

def _spec(raw):
    return A.build_spec(raw)


def test_song_level_feel_sets_swing_and_perc():
    spec = _spec({
        "title": "t", "tempo": 120,
        "defaults": {"feel": "swing", "chord_length": "q"},
        "sections": [{"name": "a", "bars": 1, "keys": "C::maj"}],
    })
    assert spec.swing == pytest.approx(0.5)
    assert spec.sections[0]["perc"]["ghost_rate"] == pytest.approx(0.08)


def test_explicit_defaults_beat_the_feel():
    spec = _spec({
        "title": "t", "tempo": 120,
        "defaults": {"feel": "swing", "swing": 0.2, "chord_length": "q",
                     "perc": {"ghost_rate": 0.5}},
        "sections": [{"name": "a", "bars": 1, "keys": "C::maj"}],
    })
    assert spec.swing == pytest.approx(0.2)
    assert spec.sections[0]["perc"]["ghost_rate"] == pytest.approx(0.5)


def test_section_feel_applies_to_that_section_only():
    spec = _spec({
        "title": "t", "tempo": 120,
        "defaults": {"chord_length": "q"},
        "sections": [
            {"name": "a", "bars": 1, "keys": "C::maj"},
            {"name": "b", "bars": 1, "keys": "G::maj", "feel": "funk"},
        ],
    })
    a, b = spec.sections
    assert a["perc"]["ghost_rate"] == pytest.approx(0.0)
    assert a["bass"].get("lock_kick") is False
    assert b["perc"]["ghost_rate"] == pytest.approx(0.22)
    assert b["bass"]["lock_kick"] is True


def test_explicit_section_values_beat_section_feel():
    spec = _spec({
        "title": "t", "tempo": 120,
        "defaults": {"chord_length": "q"},
        "sections": [
            {"name": "a", "bars": 1, "keys": "C::maj", "feel": "funk",
             "perc": {"ghost_rate": 0.02}, "bass": {"lock_kick": False}},
        ],
    })
    sec = spec.sections[0]
    assert sec["perc"]["ghost_rate"] == pytest.approx(0.02)
    assert sec["bass"]["lock_kick"] is False


def test_unknown_feel_raises():
    with pytest.raises(ValueError):
        _spec({
            "title": "t", "tempo": 120,
            "defaults": {"feel": "grunge", "chord_length": "q"},
            "sections": [{"name": "a", "bars": 1, "keys": "C::maj"}],
        })


def test_pocket_from_feel_reaches_the_drum_timeline():
    spec = _spec({
        "title": "t", "tempo": 120,
        "defaults": {"chord_length": "q",
                     "perc": {"main": "qb,qc,qb,qc"}},
        "sections": [{"name": "a", "bars": 1, "keys": "C::maj",
                      "feel": "laidback"}],
    })
    events, _ = A.build_events(spec)
    snare_hits = [h for k, _, _, hits in events if k == "drum"
                  for h in hits if h.note == 38]
    assert snare_hits
    assert all(h.timing_offset == pytest.approx(0.035) for h in snare_hits)
