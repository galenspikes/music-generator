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

---

Created by **Galen Spikes**. Copyright © 2026 Galen Spikes. Released under the
[MIT License](../LICENSE).
