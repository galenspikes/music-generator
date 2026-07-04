---
title: Music Generator
emoji: 🎵
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Music Generator — live demo

The real [React/FastAPI webapp](https://github.com/galenspikes/music-generator/tree/main/webapp)
running as a Hugging Face Docker Space: the full instrument (harmony editor,
percussion editor, instrument/soundfont pickers, presets, lead-sheet PDF
import, a static docs browser) — not a stripped-down demo.

## How it works

The [`Dockerfile`](../Dockerfile) at the repo root builds the Vite frontend,
then runs the FastAPI backend (`webapp/backend/app.py`) as a single process
that serves the built frontend, the API, and the static project showcase
(`/showcase`) all from one origin. Generation happens server-side (pure
Python — `mido`/`numpy`/`pyyaml`, no native audio deps); playback happens
client-side via the `html-midi-player` web component against a hosted
SoundFont, so the Space needs no FluidSynth/ffmpeg.

## Deploying to Hugging Face Spaces

The Space has its own git repo on Hugging Face; the GitHub repo doesn't push
to it automatically **unless** you enable the sync workflow below.

**Automatic (recommended).** `.github/workflows/deploy-space.yml` mirrors the
app source (`Dockerfile`, `requirements.txt`, the engine modules, `library/`,
`songs/`, `docs/`, `site/`, `webapp/`) plus this file (as the Space's
`README.md`) to the Space on every relevant change to `main`. Enable it once:

1. Create a write token at <https://huggingface.co/settings/tokens>.
2. In the GitHub repo, add it as a secret **`HF_TOKEN`** under
   *Settings → Secrets and variables → Actions*.

Without the secret the workflow is a harmless no-op. Adjust the `HF_SPACE`
env in the workflow if your Space path differs from `gsp87/music-generator`.

After the first sync, a Space normally only rebuilds its own container image
when its git repo changes — which the sync workflow does. If a running Space
looks stale, use *Settings → Factory reboot* to force it to rebuild.

**Manual (one-off).**
```bash
git clone https://huggingface.co/spaces/<user>/music-generator hf-space
rsync -a --delete --exclude='.git' \
  --exclude-from=.dockerignore --exclude='.github' --exclude='tests' \
  --exclude='requirements-dev.txt' --exclude='requirements-docs.txt' \
  ./ hf-space/
cp space/README.md hf-space/README.md
cd hf-space && git add -A && git commit -m "Update app" && git push
```

## Running locally

```bash
docker build -t music-generator .
docker run -p 7860:7860 music-generator
```
Or without Docker, from the repo root:
```bash
pip install -r requirements.txt
(cd webapp/frontend && npm ci && npm run build)
python -m uvicorn app:app --app-dir webapp/backend --port 7860
```
