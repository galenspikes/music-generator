"""HTTP-level tests for the FastAPI backend, via Starlette's TestClient.

Skipped automatically if the web backend's deps (fastapi/httpx) aren't
installed, so the engine test suite still runs in a minimal environment.
"""

import base64
import io
import pathlib
import sys

import mido
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

BACKEND = pathlib.Path(__file__).resolve().parents[1] / "webapp" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
from app import app  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_schema_endpoint():
    r = client.get("/api/schema")
    assert r.status_code == 200
    params = r.json()["params"]
    assert len(params) > 40
    assert all({"name", "kind", "control", "group"} <= set(p) for p in params)


def test_vocab_endpoint():
    r = client.get("/api/vocab")
    body = r.json()
    assert r.status_code == 200
    assert len(body["recipes"]) > 0
    assert len(body["drums"]) > 0
    assert len(body["instruments"]) > 0


def test_vocab_endpoint_instrument_catalog():
    # Thread D: the full, family-grouped GM catalog for the instrument picker,
    # alongside (not replacing) the short curated alias list.
    r = client.get("/api/vocab")
    body = r.json()
    catalog = body["instrument_catalog"]
    assert len(catalog) == 128
    assert all({"program", "name", "family"} <= set(e) for e in catalog)
    families = {e["family"] for e in catalog}
    assert "Piano" in families and "Bass" in families and "Strings" in families


def test_generate_endpoint_returns_midi():
    r = client.post("/api/generate", json={"spec": {
        "mode": "ostinato", "keys": "C::maj7, A::min9, G::13", "seconds": 8}})
    assert r.status_code == 200
    body = r.json()
    data = base64.b64decode(body["midi"])
    assert data[:4] == b"MThd"
    assert body["mode"] == "ostinato"
    assert body["tracks"]
    parsed = mido.MidiFile(file=io.BytesIO(data))
    notes = [m for tr in parsed.tracks for m in tr
             if m.type == "note_on" and m.velocity > 0]
    assert notes


def test_generate_endpoint_bad_input_is_422():
    r = client.post("/api/generate", json={"spec": {
        "mode": "ostinato", "keys": "C::not_a_recipe"}})
    assert r.status_code == 422


def test_validate_endpoint():
    good = client.post("/api/validate", json={"spec": {"keys": "C::maj7",
                                                       "mode": "ostinato"}})
    assert good.json()["ok"] is True
    bad = client.post("/api/validate", json={"spec": {"keys": "C::nope",
                                                      "mode": "ostinato"}})
    assert bad.json()["ok"] is False


def test_parse_keys_endpoint():
    r = client.post("/api/parse-keys",
                    json={"keys": "[A, G]*16, C::maj7", "mode": "ostinato"})
    body = r.json()
    assert body["ok"] is True
    assert body["total"] == 33
    assert any(s["type"] == "group" for s in body["segments"])


def test_parse_perc_endpoint():
    drums = client.post("/api/parse-perc",
                        json={"pattern": "qb, eg", "kind": "drums"})
    assert drums.json()["ok"] is True
    chord = client.post("/api/parse-perc",
                        json={"pattern": "ec, er", "kind": "chord"})
    assert chord.json()["tokens"][0]["hits"] == ["chord"]


def test_docs_lists_diataxis_sections():
    r = client.get("/api/docs")
    assert r.status_code == 200
    sections = r.json()["sections"]
    labels = [s["section"] for s in sections]
    # The four Diátaxis modes are present and ordered ahead of the rest.
    for expected in ["Tutorials", "How-to guides", "Reference", "Explanation"]:
        assert expected in labels
    assert labels.index("Tutorials") < labels.index("Reference")
    slugs = {d["slug"] for s in sections for d in s["docs"]}
    assert "tutorials/01-first-groove" in slugs
    # chord-recipes is served as the interactive browser, not static markdown.
    assert "reference/chord-recipes" not in slugs


def test_docs_fetch_nested_doc():
    r = client.get("/api/docs/tutorials/01-first-groove")
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "tutorials/01-first-groove"
    assert body["title"]
    assert "# " in body["content"]


def test_docs_rejects_path_traversal_and_excluded():
    assert client.get("/api/docs/../../CLAUDE").status_code == 404
    assert client.get("/api/docs/reference/chord-recipes").status_code == 404
    assert client.get("/api/docs/does/not/exist").status_code == 404


def test_recipes_endpoint():
    r = client.get("/api/recipes")
    assert r.status_code == 200
    recipes = r.json()["recipes"]
    assert len(recipes) > 0
    maj = next(x for x in recipes if x["name"] == "maj")
    assert maj["intervals"] == [0, 4, 7]
    assert maj["category"]


# --- presets (Thread B) ---------------------------------------------------------

@pytest.fixture
def presets_dir(tmp_path, monkeypatch):
    import generator_api as api
    d = tmp_path / "presets" / "user"
    monkeypatch.setattr(api, "PRESETS_DIR", d)
    return d


def test_preset_save_load_delete_roundtrip(presets_dir):
    r = client.post("/api/presets/My Groove",
                    json={"spec": {"keys": "C::maj7"}, "title": "My Groove"})
    assert r.status_code == 200

    names = {p["name"] for p in client.get("/api/presets").json()["presets"]}
    assert "my-groove" in names

    r = client.get("/api/presets/My Groove")
    assert r.status_code == 200
    assert r.json()["spec"] == {"keys": "C::maj7"}

    r = client.delete("/api/presets/My Groove")
    assert r.status_code == 200
    assert client.get("/api/presets/My Groove").status_code == 404


def test_preset_delete_missing_is_idempotent(presets_dir):
    r = client.delete("/api/presets/never-existed")
    assert r.status_code == 200


def test_preset_path_traversal_rejected(presets_dir):
    r = client.get("/api/presets/..%2F..%2F..%2Fetc%2Fpasswd")
    assert r.status_code == 404
    assert not (presets_dir.parent.parent / "etc" / "passwd.json").exists()
