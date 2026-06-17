# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""FastAPI backend for the Music Generator web instrument.

Thin HTTP layer over ``generator_api`` — the in-process seam. The engine is
driven through a typed call (spec in, structured result out), not a subprocess
or a ``sys.argv`` hack. Endpoints:

    GET  /api/health
    GET  /api/vocab     chord recipes + drum letters (editor hints)
    GET  /api/schema    every parameter, introspected from the CLI parser
    POST /api/validate  does this spec parse? (inline editor feedback)
    POST /api/generate  spec -> { midi (base64), tracks, duration, warnings }
"""

from __future__ import annotations

import base64
import json
import pathlib
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import generator_api as api  # noqa: E402

app = FastAPI(title="Music Generator", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SpecRequest(BaseModel):
    spec: dict


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/vocab")
def vocab() -> dict:
    try:
        from library.chord_recipes import CHORD_RECIPES
        recipes = sorted(CHORD_RECIPES)
    except Exception:
        recipes = []
    drums, grooves, perc_lib = {}, [], ""
    try:
        lib_path = REPO_ROOT / "library" / "percussion_library.json"
        lib = json.loads(lib_path.read_text())
        drums = lib.get("drum_map", {})
        for name, g in (lib.get("groups") or {}).items():
            grooves.append({"name": name, "bpm": g.get("bpm_hint")})
        perc_lib = str(lib_path)  # absolute, so groove lookups resolve server-side
    except Exception:
        pass
    return {"recipes": recipes, "drums": drums,
            "grooves": grooves, "perc_lib": perc_lib}


@app.get("/api/schema")
def schema() -> dict:
    return {"params": api.parameter_schema()}


@app.post("/api/validate")
def validate(req: SpecRequest) -> dict:
    return api.validate(req.spec).as_dict()


class ParseKeysRequest(BaseModel):
    keys: str = ""
    mode: str = "ostinato"


@app.post("/api/parse-keys")
def parse_keys(req: ParseKeysRequest) -> dict:
    return api.parse_keys(req.keys, req.mode)


class ParsePercRequest(BaseModel):
    pattern: str = ""
    kind: str = "drums"  # "drums" | "chord"


@app.post("/api/parse-perc")
def parse_perc(req: ParsePercRequest) -> dict:
    return api.parse_perc(req.pattern, req.kind)


@app.post("/api/generate")
def generate(req: SpecRequest) -> dict:
    try:
        result = api.generate(req.spec)
    except api.GenerationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "midi": base64.b64encode(result.midi).decode("ascii"),
        **result.as_dict(),
    }


@app.get("/api/songs")
def list_songs() -> dict:
    """List all available songs."""
    return {"songs": api.list_songs()}


@app.get("/api/songs/{name}")
def load_song(name: str) -> dict:
    """Load a song and return the spec for it."""
    try:
        spec = api.load_song(name)
    except api.GenerationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"spec": spec, "name": name}


@app.get("/api/presets")
def list_presets() -> dict:
    """List user presets."""
    return {"presets": api.list_presets()}


@app.get("/api/presets/{name}")
def load_preset(name: str) -> dict:
    """Load a user preset."""
    try:
        spec = api.load_preset(name)
    except api.GenerationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"spec": spec, "name": name}


class SavePresetRequest(BaseModel):
    spec: dict
    title: str = ""
    description: str = ""


@app.post("/api/presets/{name}")
def save_preset(name: str, req: SavePresetRequest) -> dict:
    """Save a user preset."""
    try:
        data = api.save_preset(name, req.spec, req.title, req.description)
    except api.GenerationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return data


# Serve the built frontend if present (production single-process mode).
_DIST = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="frontend")
