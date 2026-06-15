# Music Generator — offline web app (PWA)

A **fully offline, installable** web app: the project's pure-Python engine runs
**in the browser** via [Pyodide](https://pyodide.org) (Python compiled to
WebAssembly). It generates MIDI client-side — no server, no network after the
first load — and plays it back with `html-midi-player`. Works on iPhone,
Android, and desktop from one codebase; "Add to Home Screen" makes it behave
like a native app.

## How it works

```
web/
  index.html / app.js / styles.css   the app shell + UI
  manifest.webmanifest               PWA manifest (installable)
  sw.js                              service worker (precache → offline)
  icons/                             app icons (shared design with the iOS app)
  engine.zip                         the engine + vendored mido  (built; gitignored)
  pyodide/                           self-hosted Pyodide runtime  (fetched; gitignored)
  tools/build_engine.py              repo-root engine + mido -> engine.zip
  tools/fetch_pyodide.py             assemble the minimal Pyodide runtime
  tools/make_icons.py                render PWA icons from the iOS icon source
```

- **Engine in the browser:** `app.js` boots Pyodide, loads numpy + pyyaml
  (bundled with Pyodide), unpacks `engine.zip` into Pyodide's in-memory
  filesystem, points the engine at a writable dir (`MUSICGEN_OUTPUT_DIR`), and
  calls `music_generator.main()`, which returns the MIDI path. mido is pure
  Python and not in Pyodide, so it is **vendored** into `engine.zip` for offline
  use.
- **Single source of truth:** the engine is *not* duplicated in git.
  `tools/build_engine.py` bundles the repo-root modules + `library/` at build
  time (like the iOS app's `sync_engine.py`).
- **Offline:** the service worker precaches the app shell, the Pyodide runtime,
  and `engine.zip`, and cache-first-caches the CDN player + its SoundFont, so
  everything works offline after the first visit.

## Build & run locally

```bash
cd web
python tools/build_engine.py                 # -> web/engine.zip
python tools/fetch_pyodide.py                 # -> web/pyodide/ (from the CDN)
#   ...or, if the CDN is blocked: python tools/fetch_pyodide.py --from-tarball
python tools/make_icons.py                    # -> web/icons/ (already committed)

# serve over HTTP (service workers require it; file:// won't work)
python -m http.server 8000
# open http://localhost:8000/
```

First load downloads ~25 MB of Pyodide + engine and caches it; subsequent loads
(and generation) are offline.

## Deploy (GitHub Pages)

The build artifacts are gitignored, so a CI step must assemble them before
publishing. See `.github/workflows/deploy-web.yml`: it runs the three `tools/*`
scripts and publishes `web/` to Pages. Point Pages at the workflow and the app
is live at `https://<user>.github.io/music-generator/`.

## Features

- **Create**: modes (ostinato/complete, process ×3, fugue), instrument, tempo,
  length, drums, and chord-key tokens.
- **Examples**: a 100-piece demo gallery (`examples.json`, every entry validated
  against the engine) grouped by genre — tap to generate & play.
- **Library**: save up to 10 generated pieces to the device (localStorage),
  replay / edit / delete.
- **Planned**: a visual token builder (drag-and-drop chips, mobile-first) — see
  `docs/web-token-builder-plan.md`.

## Notes / roadmap

- Engine generation is **fully offline** (verified headlessly under Pyodide).
- Playback uses `html-midi-player` + its hosted SoundFont, cached by the service
  worker. For guaranteed-offline audio with the bundled `.sf2`, a WASM SoundFont
  synth (e.g. spessasynth) is the future upgrade.
- numpy/pyyaml come from Pyodide; mido is vendored. Pinned to Pyodide 0.26.2.
