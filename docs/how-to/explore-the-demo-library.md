# How to explore the demo library and song catalog

*Goal: play the curated demos, browse what's rendered, and find your own past
renders.*

## Demo library

`cook_song.py` is one catalog over two kinds of demo:

- **Songs** — full multi-section arrangements in `songs/*.yml` (the "press
  demo" tunes). The flagship is **Kiss On My List**.
- **Presets** — capability showcases in `library/song_cookbook.py` that demo
  the things a song file can't: fugue, process music, dense/exotic voicing,
  melody transforms, and evolving percussion.

```bash
make demo                          # play the flagship (Kiss On My List)
make gallery                       # render the highlight set to site/assets/midi

python cook_song.py list           # every demo (songs + presets)
python cook_song.py show kiss      # details for one demo
python cook_song.py make kiss      # render + play a song
python cook_song.py make fugue     # render + play a preset
python cook_song.py make fugue -- --sf2 SoundFonts/arachno.sf2   # forward args
```

Songs: `kiss`, `autumn_leaves`, `girl_from_ipanema`, `isnt_she_lovely`,
`riders_on_the_storm`, `whiter_shade_of_pale`, `yesterday`. Several carry a
real melody line (scale-degree grammar) on top of the arrangement.

Presets: `dense_colors`, `counterpoint`, `fugue`, `process_additive`,
`process_additive_long` (~8 min), `process_phase`, `process_phase_5min`,
`process_phase_20min`, `melody_transforms`, `perc_evolution`, `salsa`,
`rock`, `rnb`, `bach_prelude`, `bach_counterpoint`.

A browser-playable gallery (rendered MIDI, no SoundFont needed) lives in
[`site/`](../../site/index.html) — regenerate it with `make gallery`.

Add your own preset to `library/song_cookbook.py`:

```python
"my_style": {
    "title": "My Custom Style",
    "description": "A unique musical approach",
    "args": ["--chords", "extended-chords", "--satb-style", "counterpoint"],
}
```

## Song catalog

Every render appends an entry to `output/master_catalog.json` (generation
args, timestamps, and output paths). Query it with `query_catalog.py`:

```bash
venv/bin/python query_catalog.py list [limit]   # recent songs (default 10)
venv/bin/python query_catalog.py search <query> # match keys/name/instrument/out
venv/bin/python query_catalog.py show <name>    # full details for one song
venv/bin/python query_catalog.py stats          # totals, instruments, BPM range
```

The catalog lives under the gitignored `output/`, so it's local to your
machine.

## See also

- [Create an arrangement](create-an-arrangement.md)
- [Render audio](render-audio.md)
