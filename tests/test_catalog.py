"""Master-catalog tests: the update side (music_generator.update_master_catalog).
These pin the robustness of catalog writing against missing fields / malformed files.
"""

import json

import music_generator as mg


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
