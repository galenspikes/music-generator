# Music Generator — web instrument

A schema-driven web UI for the [Music Generator](https://github.com/galenspikes/music-generator):
a "digital music box" that exposes every engine parameter as a tactile control
(knobs, switches, chips, token fields) in a modular-synth-style rack. Edit a
chord or percussion token, turn a knob, and hear it instantly.

- **`backend/`** — FastAPI service over `generator_api.py` (the in-process seam).
  Generation happens in memory; the API returns MIDI plus structured stem info.
- **`frontend/`** — React + Vite. The control surface is generated from the
  engine's own parameter schema, so it always reflects the full feature set.
- **`chords-frontend/`** — a separate, standalone, installable (PWA) instrument
  focused purely on chord progressions: a tap-driven builder (no typing tokens
  or numbers — root/quality/inversion/bass are all popups and steppers),
  instant client-side soundfont playback, and a saved-progression library.
  Shares the same backend but is its own Vite project, mounted at `/chords`.
- **`shared/`** — a few fetch wrappers over the API, used by both frontends
  (`frontend/` and `chords-frontend/`) so the token/recipe contract lives in
  one place.

## Run (dev)

```bash
# backend (from repo root, with the project venv)
PYTHONPATH=$PWD venv/bin/uvicorn app:app --app-dir webapp/backend --port 8753

# main frontend
cd webapp/frontend && npm install && npm run dev

# standalone Chord Recipes instrument
cd webapp/chords-frontend && npm install && npm run dev
```

Each Vite dev server proxies `/api` to the backend; open the printed localhost URL.

---

Created by **Galen Spikes**. Copyright © 2026 Galen Spikes. Released under the
[MIT License](../LICENSE).
