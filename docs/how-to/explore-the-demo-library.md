# How to explore the demo library

*Goal: play the curated demos and browse what's rendered.*

## Demo library

Two kinds of demo live in the repo:

- **Songs** — full multi-section arrangements in `songs/*.yml` (the "press
  demo" tunes). The flagship is **Kiss On My List**.
- **Presets** — capability showcases in `library/song_cookbook.py` that demo
  the things a song file can't: dense/exotic voicing, counterpoint, and
  evolving percussion.

```bash
make demo                          # play the flagship (Kiss On My List)
make gallery                       # render the highlight set to site/assets/midi

venv/bin/python music_generator.py --song songs/kiss.yml --out kiss --no-play
./play_music --sf2 SoundFonts/arachno.sf2 --song songs/isnt_she_lovely.yml
```

A preset's args live in `library/song_cookbook.py`; run one directly:

```bash
venv/bin/python -c "
from library.song_cookbook import resolve_recipe, format_command
_, payload = resolve_recipe('dense_colors')
print(format_command(payload['args']))
"
# then paste the printed args after music_generator.py or play_music
```

Songs: `kiss`, `autumn_leaves`, `girl_from_ipanema`, `isnt_she_lovely`,
`riders_on_the_storm`, `whiter_shade_of_pale`, `yesterday`. Several carry a
real melody line (scale-degree grammar) on top of the arrangement.

Presets: `dense_colors`, `counterpoint`, `bach_prelude`, `bach_counterpoint`,
`perc_evolution`, `salsa`, `rock`, `rnb`.

A browser-playable gallery (rendered MIDI, no SoundFont needed) lives in
[`site/`](../../site/index.html) — regenerate it with `make gallery`
(runs `render_gallery.py`).

Add your own preset to `library/song_cookbook.py`:

```python
"my_style": {
    "title": "My Custom Style",
    "description": "A unique musical approach",
    "args": ["--chords", "extended-chords", "--satb-style", "counterpoint"],
}
```

## See also

- [Create an arrangement](create-an-arrangement.md)
- [Render audio](render-audio.md)
