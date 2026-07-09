"""The SQLite progression store (progression_store.py) and its
generator_api facades: CRUD shapes, legacy-JSON migration, search, and
concurrent access.
"""
import json
import threading

import pytest

import generator_api as api
from progression_store import ProgressionStore


@pytest.fixture
def store(tmp_path):
    return ProgressionStore(tmp_path / "progressions.db",
                            legacy_dir=tmp_path)


class TestCrud:
    def test_save_returns_record_shape(self, store):
        data = store.save("ii-v-i", "D::min7, G::7, C::maj7",
                          title="ii-V-I", tags=["jazz"], tempo=96)
        assert data["title"] == "ii-V-I"
        assert data["tags"] == ["jazz"]
        assert data["keys"] == "D::min7, G::7, C::maj7"
        assert data["tempo"] == 96
        assert data["voicing"] is None
        assert data["saved"]

    def test_load_roundtrip(self, store):
        saved = store.save("blues", "C::7, F::7, G::7", tags=["blues"],
                           voicing="dense")
        assert store.load("blues") == saved

    def test_load_missing_returns_none(self, store):
        assert store.load("nope") is None

    def test_save_overwrites(self, store):
        store.save("x", "C, G", title="first")
        store.save("x", "C, F", title="second")
        loaded = store.load("x")
        assert loaded["title"] == "second"
        assert loaded["keys"] == "C, F"
        assert len(store.list()) == 1

    def test_title_defaults_to_name(self, store):
        assert store.save("my-prog", "C")["title"] == "my-prog"

    def test_list_summary_shape_and_order(self, store):
        store.save("b", "G", tags=["t"])
        store.save("a", "C", tempo=90)
        listed = store.list()
        assert [p["name"] for p in listed] == ["a", "b"]
        for p in listed:
            assert set(p) == {"name", "title", "tags", "keys", "tempo", "saved"}

    def test_delete_is_idempotent(self, store):
        store.save("gone", "C")
        store.delete("gone")
        store.delete("gone")  # second delete: no error
        assert store.load("gone") is None


class TestSearch:
    def test_substring_matches_name_title_keys(self, store):
        store.save("ii-v-i", "D::min7, G::7, C::maj7", title="Jazz turnaround")
        store.save("blues", "C::7, F::7", title="12-bar")
        assert [p["name"] for p in store.search("jazz")] == ["ii-v-i"]
        assert [p["name"] for p in store.search("12-bar")] == ["blues"]
        assert [p["name"] for p in store.search("min7")] == ["ii-v-i"]

    def test_tag_filter_is_exact(self, store):
        store.save("a", "C", tags=["jazz", "ballad"])
        store.save("b", "G", tags=["jazzy"])
        assert [p["name"] for p in store.search(tag="jazz")] == ["a"]

    def test_empty_search_lists_all(self, store):
        store.save("a", "C")
        store.save("b", "G")
        assert store.search() == store.list()


class TestLegacyMigration:
    def test_json_files_imported_once(self, tmp_path):
        legacy = {"title": "Old One", "tags": ["legacy"], "keys": "C, G",
                  "tempo": 100, "voicing": None, "saved": "2025-01-01T00:00:00"}
        (tmp_path / "old-one.json").write_text(json.dumps(legacy))
        (tmp_path / "broken.json").write_text("{not json")  # skipped, not fatal

        store = ProgressionStore(tmp_path / "p.db", legacy_dir=tmp_path)
        assert store.load("old-one") == legacy
        assert [p["name"] for p in store.list()] == ["old-one"]
        # the legacy file is left in place but is no longer the source of truth
        assert (tmp_path / "old-one.json").exists()

    def test_db_row_beats_legacy_file(self, tmp_path):
        store = ProgressionStore(tmp_path / "p.db", legacy_dir=tmp_path)
        store.save("dup", "C, F", title="from-db")
        (tmp_path / "dup.json").write_text(json.dumps({"title": "from-file",
                                                       "keys": "X"}))
        fresh = ProgressionStore(tmp_path / "p.db", legacy_dir=tmp_path)
        assert fresh.load("dup")["title"] == "from-db"


class TestConcurrency:
    def test_parallel_saves_all_land(self, store):
        def save(i):
            store.save(f"p{i}", f"C*{i + 1}", tags=[f"t{i % 3}"])

        threads = [threading.Thread(target=save, args=(i,)) for i in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(store.list()) == 16
        assert len(store.search(tag="t0")) == 6


class TestApiFacades:
    @pytest.fixture(autouse=True)
    def _tmp_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(api, "PROGRESSIONS_DIR", tmp_path / "progressions")

    def test_save_load_delete_via_api(self):
        api.save_progression("My Prog!", "C::maj7, F::maj7", title="Mine")
        loaded = api.load_progression("My Prog!")  # slugified consistently
        assert loaded["keys"] == "C::maj7, F::maj7"
        assert "my-prog" in [p["name"] for p in api.list_progressions()]
        api.delete_progression("My Prog!")
        with pytest.raises(api.GenerationError):
            api.load_progression("My Prog!")

    def test_search_facade(self):
        api.save_progression("axis", "C, G, Am, F", tags=["pop"])
        api.save_progression("anatole", "C, A::7, D::min7, G::7", tags=["jazz"])
        assert [p["name"] for p in api.search_progressions(tag="pop")] == ["axis"]
        assert [p["name"] for p in api.search_progressions("anatole")] == ["anatole"]
