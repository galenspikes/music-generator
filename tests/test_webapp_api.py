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
    # named grooves + the library path (for perc_main_key / perc_intr_keys)
    assert len(body["grooves"]) > 0
    assert all("name" in g for g in body["grooves"])
    assert body["perc_lib"].endswith("percussion_library.json")


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
