# Music Generator — iOS app (offline)

A native, **fully offline** iOS build of the Music Generator. The project's
pure-Python engine (the token DSL → MIDI generator) runs on-device via
[BeeWare/Briefcase](https://beeware.org); playback is native through
`AVMIDIPlayer` and a bundled SoundFont. No server, no network, no FluidSynth or
ffmpeg.

## How it fits together

```
ios/
  pyproject.toml            Briefcase config (app id, deps)
  tools/sync_engine.py      vendors the repo-root engine into _engine/ (gitignored)
  src/musicgen/
    app.py                  Toga UI: pick a style / type chords, generate, play
    generate.py             runs the engine on-device, returns the MIDI path
    playback.py             AVMIDIPlayer bridge (rubicon-objc) for native playback
    _engine/                vendored engine (created by sync_engine.py; not in git)
    resources/default_gm.sf2  bundled GM SoundFont (~300 KB; plays out of the box)
    resources/soundfont.sf2   optional higher-quality font you supply (not in git)
```

**Single source of truth:** the engine is *not* duplicated in git. The repo root
(`music_generator.py`, `melody.py`, `library/`, …) is canonical;
`sync_engine.py` copies it into `_engine/` at build time. Re-run it whenever the
engine changes.

The only engine change needed for embedding was making the output directory
overridable (`MUSICGEN_OUTPUT_DIR`) and having `main()` return the MIDI path —
both already on `main`. The DSL and generation logic are untouched.

## Build & run (requires macOS + Xcode)

Briefcase can only build iOS apps on macOS. From `ios/`:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install briefcase

# 1. Vendor the engine (a GM SoundFont is already bundled — see below)
python tools/sync_engine.py

# 2. Create / build / run
briefcase create iOS
briefcase build iOS
briefcase run iOS            # boots the Simulator

# Optional: install a higher-quality font (app prefers it over the default)
python tools/fetch_soundfont.py
```

To iterate after editing engine or app code, re-run `sync_engine.py` then
`briefcase update iOS -r && briefcase run iOS`.

### Desktop smoke test (no Mac required)

The generation half is platform-independent and can be exercised anywhere
(playback needs the iOS ObjC runtime, so it's skipped):

```bash
python tools/sync_engine.py
python -c "from src.musicgen import generate as g; \
print(g.generate(['--mode','ostinato','--keys','C::maj7, A::min9','--seconds','8'], \
output_dir='/tmp/mg-ios'))"
```

## Dependencies

- `mido`, `numpy`, `pyyaml` — the engine's pure-Python deps (numpy ships as a
  BeeWare-provided iOS binary wheel).
- `rubicon-objc` — calls AVFoundation from Python for playback.

`AVFoundation` is part of the iOS SDK and is linked by the Briefcase-generated
Xcode project; no extra setup is normally required.

## Status / roadmap

- [x] Engine runs on-device, writing to an app-writable directory.
- [x] Native offline playback via `AVMIDIPlayer` + bundled SoundFont.
- [x] Toga UI: style presets (from the song cookbook) + custom chord keys.
- [x] Bundle a default SoundFont (plays out of the box).
- [x] App icon (`tools/make_icon.py` → `resources/musicgen.png`).
- [x] Share/export the generated `.mid` via the native iOS share sheet.
- [ ] Expose more engine controls (tempo, instrument, percussion, arrangements).
- [ ] Optional rendered-audio export (offline render to WAV/AAC).
- [ ] Optional native SwiftUI shell over the embedded engine for a richer UI.
```
