---
title: Music Generator
emoji: ♪
colorFrom: yellow
colorTo: indigo
sdk: gradio
sdk_version: 4.44.0
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

1. Create a new Space: SDK **Gradio**, hardware **CPU basic** (free).
2. Push the contents of this `space/` folder to the Space's git repo:
   ```bash
   git clone https://huggingface.co/spaces/<user>/music-generator hf-space
   cp space/app.py space/requirements.txt space/README.md hf-space/
   cd hf-space && git add . && git commit -m "Add app" && git push
   ```
3. The Space builds from `requirements.txt` and launches `app.py`.

## Running locally

```bash
pip install -r space/requirements.txt
python space/app.py
```
Run from the repo root so the app finds `music_generator.py` next to it.
