# Music Generator — web instrument

A schema-driven web UI for the [Music Generator](https://github.com/galenspikes/music-generator):
a "digital music box" that exposes every engine parameter as a tactile control
(knobs, switches, chips, token fields) in a modular-synth-style rack. Edit a
chord or percussion token, turn a knob, and hear it instantly.

- **`backend/`** — FastAPI service over `generator_api.py` (the in-process seam).
  Generation happens in memory; the API returns MIDI plus structured stem info.
- **`frontend/`** — React + Vite. The control surface is generated from the
  engine's own parameter schema, so it always reflects the full feature set.

## Run (dev)

```bash
# backend (from repo root, with the project venv)
PYTHONPATH=$PWD venv/bin/uvicorn app:app --app-dir webapp/backend --port 8753

# frontend
cd webapp/frontend && npm install && npm run dev
```

The Vite dev server proxies `/api` to the backend; open the printed localhost URL.

## Deploy (production)

**Frontend build:**
```bash
cd webapp/frontend && npm install && npm run build
# output → webapp/frontend/dist/
```

**Single-process serve** (backend mounts built frontend):
```bash
PYTHONPATH=$PWD venv/bin/uvicorn app:app --app-dir webapp/backend --port 8000
```

The backend automatically serves the built frontend at `/` if `webapp/frontend/dist/` exists.
Open `http://localhost:8000`.

**Or separate servers** (frontend on CDN/static host, backend on app server):
- Build frontend as above
- Host `webapp/frontend/dist/` on a web server or CDN
- Run backend on an app server (Heroku, Fly.io, your VPS, etc.)
- Update frontend's API proxy in `vite.config.js` to point to the backend

---

Created by **Galen Spikes**. Copyright © 2026 Galen Spikes. Released under the
[MIT License](../LICENSE).
