"""Master-catalog tests: the update side (music_generator.update_master_catalog)
and the query side (query_catalog). These pin the round-trip and the
robustness of both against missing fields / malformed files.
"""

import json

import pytest

import music_generator as mg
import query_catalog as qc


def _write_manifest(tmp_path, **overrides):
    """Write a minimal manifest sidecar and return its path."""
    manifest = {
        "file_catalog": {"base_name": overrides.get("base_name", "song_a")},
        "generated_utc": "2026-07-02T00:00:00Z",
        "midi": "output/midi/song_a/song_a.mid",
        "audio": "",
        "metadata": "",
        "args": {
            "keys": overrides.get("keys", "C::maj7, A::min9"),
            "bpm": overrides.get("bpm", 120),
            "seconds": overrides.get("seconds", 60),
            "instrument": overrides.get("instrument", "piano"),
            "out": overrides.get("out", "song_a"),
        },
    }
    p = tmp_path / f"{overrides.get('base_name', 'song_a')}.args.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    return str(p)


def test_update_master_catalog_roundtrip(tmp_path, monkeypatch):
    catalog_path = tmp_path / "master_catalog.json"
    monkeypatch.setattr(mg, "OUTPUT_DIR", tmp_path)

    m1 = _write_manifest(tmp_path, base_name="song_a", keys="C::maj7")
    mg.update_master_catalog(m1)

    data = json.loads(catalog_path.read_text())
    assert len(data["songs"]) == 1
    assert data["songs"][0]["base_name"] == "song_a"
    assert data["songs"][0]["keys"] == "C::maj7"
    assert data["last_updated"]

    # A second, distinct manifest appends; re-adding the first is a no-op.
    m2 = _write_manifest(tmp_path, base_name="song_b")
    mg.update_master_catalog(m2)
    mg.update_master_catalog(m1)
    data = json.loads(catalog_path.read_text())
    assert len(data["songs"]) == 2


def test_update_master_catalog_survives_malformed_existing(tmp_path, monkeypatch):
    catalog_path = tmp_path / "master_catalog.json"
    monkeypatch.setattr(mg, "OUTPUT_DIR", tmp_path)
    # Legacy/corrupt shape: a list instead of the expected {"songs": [...]}.
    catalog_path.write_text(json.dumps(["garbage"]), encoding="utf-8")

    m1 = _write_manifest(tmp_path, base_name="song_a")
    mg.update_master_catalog(m1)  # must not raise

    data = json.loads(catalog_path.read_text())
    assert data["songs"][0]["base_name"] == "song_a"


def test_update_master_catalog_skips_unreadable_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(mg, "OUTPUT_DIR", tmp_path)
    mg.update_master_catalog(str(tmp_path / "does_not_exist.json"))
    assert not (tmp_path / "master_catalog.json").exists()


def test_query_load_catalog_missing(tmp_path, capsys):
    result = qc.load_catalog(tmp_path / "nope.json")
    assert result is None
    assert "No catalog found" in capsys.readouterr().out


def test_query_load_catalog_malformed(tmp_path, capsys):
    p = tmp_path / "master_catalog.json"
    p.write_text('{"not_songs": 1}', encoding="utf-8")
    assert qc.load_catalog(p) is None
    assert "malformed" in capsys.readouterr().out


def test_query_handles_entries_missing_fields(capsys):
    # An entry missing keys/instrument/etc must not raise in any view.
    catalog = {"songs": [{"base_name": "sparse"}], "last_updated": "x"}
    qc.list_songs(catalog)
    qc.search_songs(catalog, "sparse")
    qc.show_song_details(catalog, "sparse")
    qc.show_stats(catalog)
    out = capsys.readouterr().out
    assert "sparse" in out


def test_query_search_and_stats(capsys):
    catalog = {
        "songs": [
            {"base_name": "jazz1", "keys": "C::maj7", "instrument": "piano",
             "out": "jazz1", "bpm": 120, "seconds": 60},
            {"base_name": "rock1", "keys": "E::min", "instrument": "distguitar",
             "out": "rock1", "bpm": 140, "seconds": 90},
        ],
        "last_updated": "2026-07-02T00:00:00Z",
    }
    qc.search_songs(catalog, "piano")
    assert "jazz1" in capsys.readouterr().out

    qc.show_stats(catalog)
    stats = capsys.readouterr().out
    assert "Total songs: 2" in stats
    assert "BPM range: 120-140" in stats
