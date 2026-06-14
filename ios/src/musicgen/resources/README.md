# Bundled SoundFont

On-device playback (`playback.py` → `AVMIDIPlayer`) renders the generated MIDI
through a SoundFont. Place one here named exactly:

    soundfont.sf2

It is **not committed** (SoundFonts are large binaries; see the repo
`.gitignore`). Pick any General MIDI `.sf2`. Good small/free options:

- **GeneralUser GS** (~30 MB, permissive license) — recommended.
- **FluidR3 GM** (~140 MB) — fuller sound, larger app.

App Store size note: the SoundFont ships inside the app bundle, so prefer a
compact font. AVMIDIPlayer also accepts a `.dls` bank if you prefer.

After adding the file, (re)build:

    python ../../tools/sync_engine.py   # from ios/, vendor the engine
    briefcase run iOS
