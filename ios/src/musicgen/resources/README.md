# SoundFont

On-device playback (`playback.py` → `AVMIDIPlayer`) renders the generated MIDI
through a SoundFont.

## Bundled default (ships with the app)

`default_gm.sf2` — **Vintage Dreams Waves v2.0** by Ian Wilson: a complete
General MIDI font (136 presets) at only ~300 KB, freely redistributable and
small enough to bundle. Sourced from the
[FluidSynth](https://github.com/FluidSynth/fluidsynth/tree/master/sf2) project.
This is the only SoundFont committed to git (a `.gitignore` exception); it makes
the app play out of the box.

## Using a higher-quality font (optional)

Drop your own General MIDI `.sf2` here named exactly:

    soundfont.sf2

The app prefers it over the bundled default. It is **not committed** (the
`.gitignore` keeps all `*.sf2` out except `default_gm.sf2`), so larger fonts stay
local. `tools/fetch_soundfont.py` can download a richer font for you:

    python tools/fetch_soundfont.py            # GeneralUser-style / FluidR3 GM

Good options: **GeneralUser GS** (~30 MB, permissive) or **FluidR3 GM**
(~140 MB, fuller). AVMIDIPlayer also accepts a `.dls` bank. Keep app size in mind
— the font ships inside the bundle.
