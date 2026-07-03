---
title: Music Generator
emoji: 🎹
colorFrom: yellow
colorTo: indigo
sdk: gradio
sdk_version: 5.50.0
python_version: "3.12"
app_file: app.py
pinned: false
license: mit
---

# Music Generator — live demo

A Gradio front end for [galenspikes/music-generator](https://github.com/galenspikes/music-generator).
Describe chords or a melodic process, generate MIDI on the server, and play it
back in the browser.

## How it works

The server runs the generator's CLI, which is pure Python (`mido` / `numpy`), to
produce a MIDI file. Playback is handled client-side by the
[html-midi-player](https://github.com/cifkao/html-midi-player) web component
using a hosted SoundFont, so the Space needs no FluidSynth, ffmpeg, or SoundFont.
On startup `app.py` clones the generator repo if it is not already present (set
`GENERATOR_REPO` to point at a fork).

## Deploying to Hugging Face Spaces

The Space has its own git repo on Hugging Face; the GitHub repo does not deploy
to it automatically **unless** you enable the sync workflow below. On startup
`app.py` clones (and, on later reboots, `git pull`s) the generator repo, so the
engine, songs, and presets always track the latest `main` — but the Gradio UI
itself is whatever `app.py` the Space is running, so keep it in sync.

**Automatic (recommended).** `.github/workflows/deploy-space.yml` pushes
`space/app.py`, `requirements.txt`, and `README.md` to the Space on every change
to `main`. Enable it once:

1. Create a write token at <https://huggingface.co/settings/tokens>.
2. In the GitHub repo, add it as a secret **`HF_TOKEN`** under
   *Settings → Secrets and variables → Actions*.

Without the secret the workflow is a harmless no-op. Adjust the `HF_SPACE`
env in the workflow if your Space path differs from `gsp87/music-generator`.

**Manual (one-off).**
```bash
git clone https://huggingface.co/spaces/<user>/music-generator hf-space
cp space/app.py space/requirements.txt space/README.md hf-space/
cd hf-space && git add . && git commit -m "Update app" && git push
```
The Space builds from `requirements.txt` and launches `app.py`.

## Running locally

```bash
pip install -r space/requirements.txt
python space/app.py
```
Run from the repo root so the app finds `music_generator.py` next to it.
