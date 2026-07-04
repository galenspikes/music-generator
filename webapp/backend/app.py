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
    GET  /api/docs      the docs/ tree (Diátaxis sections) for the Docs tab
    GET  /api/docs/{slug}  one doc's raw markdown (slug = path under docs/)
    GET  /api/recipes   chord-recipe catalog (category, intervals, notes) for
                         the interactive recipe browser
    POST /api/leadsheet/extract  upload a lead-sheet PDF -> chart + song.yml
    POST /api/leadsheet/emit     re-emit song.yml from an edited chart
    GET/POST/DELETE /api/progressions[/{name}]  saved chord-progression library
                         (for the standalone Chord Recipes app, mounted at /chords)
"""

from __future__ import annotations

import base64
import io
import json
import mimetypes
import pathlib
import sys

# stdlib doesn't know this extension; without it StaticFiles serves the PWA
# manifest as application/octet-stream, which trips some installability checks.
mimetypes.add_type("application/manifest+json", ".webmanifest")

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import generator_api as api  # noqa: E402
import leadsheet  # noqa: E402
import leadsheet_extract  # noqa: E402

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
    instruments = []
    instrument_catalog = []
    try:
        import music_generator as mg
        instruments = sorted(mg.GM_ALIASES.keys())
        instrument_catalog = list(mg.GM_CATALOG)
    except Exception:
        pass
    return {"recipes": recipes, "drums": drums,
            "grooves": grooves, "perc_lib": perc_lib,
            "instruments": instruments,
            "instrument_catalog": instrument_catalog}


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


@app.delete("/api/presets/{name}")
def delete_preset(name: str) -> dict:
    """Delete a user preset (idempotent: deleting a missing preset is not an error)."""
    api.delete_preset(name)
    return {"ok": True}


@app.get("/api/progressions")
def list_progressions() -> dict:
    """List saved chord progressions."""
    return {"progressions": api.list_progressions()}


@app.get("/api/progressions/{name}")
def load_progression(name: str) -> dict:
    """Load a saved chord progression."""
    try:
        data = api.load_progression(name)
    except api.GenerationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return data


class SaveProgressionRequest(BaseModel):
    keys: str
    title: str = ""
    tags: list[str] = []
    tempo: int | None = None
    voicing: str | None = None


@app.post("/api/progressions/{name}")
def save_progression(name: str, req: SaveProgressionRequest) -> dict:
    """Save a chord progression."""
    try:
        data = api.save_progression(name, req.keys, req.title, req.tags, req.tempo, req.voicing)
    except api.GenerationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return data


@app.delete("/api/progressions/{name}")
def delete_progression(name: str) -> dict:
    """Delete a saved chord progression (idempotent)."""
    api.delete_progression(name)
    return {"ok": True}


# Lead-sheet import (docs/design-notes/leadsheet-import-plan.md Stage 1,
# option A — deterministic text-layer extraction, no LLM in the loop). The
# uploaded PDF is read entirely in memory and discarded; nothing is written
# to disk (matches generator_api.generate()'s "never writes to output/").
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


class EmitChartRequest(BaseModel):
    chart: dict
    transpose: int = 0


def _chart_response(chart: dict, warnings: list[str]) -> dict:
    song_yaml = None
    if chart.get("sections"):
        try:
            song_yaml = leadsheet.ir_to_song_yml(chart)
        except leadsheet.LeadSheetError as exc:
            warnings = [*warnings, f"Couldn't generate song.yml yet: {exc}"]
    return {"chart": chart, "warnings": warnings, "song_yaml": song_yaml}


@app.post("/api/leadsheet/extract")
async def extract_leadsheet(file: UploadFile) -> dict:
    """Upload a lead-sheet PDF; extract its chords/form via the text layer."""
    data = await file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="PDF too large (20 MB limit).")
    try:
        result = leadsheet_extract.extract_pdf_chart(io.BytesIO(data))
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Couldn't read that as a PDF: {exc}") from exc
    return _chart_response(result.chart, result.warnings)


@app.post("/api/leadsheet/emit")
def emit_leadsheet(req: EmitChartRequest) -> dict:
    """Re-emit song.yml from a chart the user has edited in the review UI."""
    try:
        song_yaml = leadsheet.ir_to_song_yml(req.chart, transpose=req.transpose)
    except leadsheet.LeadSheetError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"song_yaml": song_yaml}


# The full docs/ tree (Diátaxis: tutorials / how-to / reference / explanation,
# plus design-notes, token-grammar deep-dives, about) surfaced in the in-app
# Docs tab. Slugs are the doc's path under docs/ without the .md suffix (e.g.
# "tutorials/01-first-groove"); every request re-resolves the path and checks
# it stays inside DOCS_DIR, so the slug can't be used to escape the tree.
# reference/chord-recipes is excluded — the webapp renders it as the
# interactive recipe browser (/api/recipes) instead of static markdown.
DOCS_DIR = REPO_ROOT / "docs"
_DOC_EXCLUDE = {"reference/chord-recipes"}

# Diátaxis sections shown in the docs sidebar, in this order. Each maps a
# top-level docs/ subdirectory to a friendly section label; anything not
# listed here is grouped under "More" so new dirs still appear.
_DOC_SECTIONS = [
    ("tutorials", "Tutorials"),
    ("how-to", "How-to guides"),
    ("reference", "Reference"),
    ("explanation", "Explanation"),
    ("token-grammar", "Token grammar"),
    ("design-notes", "Design notes"),
    ("about", "About"),
]


def _doc_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def _resolve_doc(slug: str) -> pathlib.Path | None:
    """Map a slug to its .md path, or None if it escapes DOCS_DIR / is hidden."""
    if slug in _DOC_EXCLUDE:
        return None
    path = (DOCS_DIR / f"{slug}.md").resolve()
    try:
        path.relative_to(DOCS_DIR.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


@app.get("/api/docs")
def list_docs() -> dict:
    # Collect every doc, keyed by its slug, with the section it belongs to.
    entries: dict[str, list[dict]] = {}
    for path in sorted(DOCS_DIR.rglob("*.md")):
        slug = path.relative_to(DOCS_DIR).with_suffix("").as_posix()
        if slug in _DOC_EXCLUDE:
            continue
        top = path.relative_to(DOCS_DIR).parts[0]
        # A file directly under docs/ (e.g. docs/index.md) has no subdir.
        section = top if (DOCS_DIR / top).is_dir() else "_root"
        entries.setdefault(section, []).append(
            {"slug": slug, "title": _doc_title(path.read_text(), slug)}
        )

    sections = []
    for key, label in _DOC_SECTIONS:
        if entries.get(key):
            sections.append({"section": label, "docs": entries.pop(key)})
    # Any leftover sections (new dirs, loose root files) under a catch-all.
    leftover = [d for docs in entries.values() for d in docs]
    if leftover:
        sections.append({"section": "More", "docs": sorted(leftover, key=lambda d: d["slug"])})
    return {"sections": sections}


@app.get("/api/docs/{slug:path}")
def get_doc(slug: str) -> dict:
    path = _resolve_doc(slug)
    if path is None:
        raise HTTPException(status_code=404, detail="Doc not found")
    text = path.read_text()
    return {"slug": slug, "title": _doc_title(text, slug), "content": text}


@app.get("/api/recipes")
def recipes() -> dict:
    from library.chord_recipes import recipe_catalog
    return {"recipes": recipe_catalog()}


# Serve the scholarly landing page (site/) so it's reachable from the webapp
# without a second server. In dev the Vite proxy forwards /showcase here;
# mounted before the catch-all "/" below so it wins for /showcase paths.
_SITE = REPO_ROOT / "site"
if _SITE.is_dir():
    app.mount("/showcase", StaticFiles(directory=str(_SITE), html=True), name="showcase")


# Serve the built standalone Chord Recipes instrument (webapp/chords-frontend),
# a separate PWA-installable app sharing this same backend.
_CHORDS_DIST = pathlib.Path(__file__).resolve().parent.parent / "chords-frontend" / "dist"
if _CHORDS_DIST.is_dir():
    app.mount("/chords", StaticFiles(directory=str(_CHORDS_DIST), html=True), name="chords")


# Serve the built frontend if present (production single-process mode).
_DIST = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="frontend")
