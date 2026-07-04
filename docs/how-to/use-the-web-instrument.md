# How to use the web instrument

*Goal: run the React + FastAPI web UI — a tactile control surface over the engine
where editing a token or turning a knob regenerates and plays instantly.*

## Run it (dev)

From the repo root, with the project venv and Node installed:

```bash
# backend — FastAPI over generator_api.py (in-process generation)
PYTHONPATH=$PWD venv/bin/uvicorn app:app --app-dir webapp/backend --port 8753

# frontend — React + Vite
cd webapp/frontend && npm install && npm run dev
```

The Vite dev server proxies `/api` to the backend; open the printed localhost URL.

## How it's wired

- **`webapp/backend/`** — a FastAPI service over `generator_api.py`, the in-process
  API seam. Generation happens in memory; the API returns MIDI plus stem info.
- **`webapp/frontend/`** — the control surface is generated from the engine's own
  parameter schema, so it always reflects the full feature set. The chord and
  percussion token editors write the same tokens documented in the
  [token grammar](../reference/token-grammar.md).

## Offline / PWA

The app also ships a Pyodide-based PWA path that runs the engine **in the browser**
(no backend), which is what makes an in-docs interactive playground feasible as a
future stretch goal.

## See also
[webapp/README.md](https://github.com/galenspikes/music-generator/blob/main/webapp/README.md) · [webapp UI design note](../design-notes/webapp-ui-design.md) ·
[architecture — web instrument](../explanation/architecture.md)
