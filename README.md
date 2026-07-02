---
title: Music Generator
emoji: 🎵
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Music Generator

A Python music-generation system. A compact token DSL describes chords,
percussion, and melodies; the engine realizes them into harmony, voices, and
percussion, writes a MIDI file, and optionally renders audio through FluidSynth.
It supports ostinato grooves, evolving long-form arrangements, fugal
expositions, and minimalist process music.

The token DSL is the core of the project; the
[token grammar reference](docs/reference/token-grammar.md) documents it in full.

**Live demo:** a hosted web UI for generating and hearing pieces lives in
[`space/`](space/) (a Gradio app for Hugging Face Spaces). A static project
showcase lives in [`site/`](site/) (served via GitHub Pages).

## Features

### Harmony generation
- Multiple chord families: triads, sevenths, ninths, extended chords, chromatic
  mediants, quartal harmony, suspended chords, lydian dominant.
- SATB voicing styles: block chords, counterpoint lines, arpeggiated patterns.
- Voice leading with suspensions, anticipations, and intelligent part writing.
- Custom chord recipes via colon notation: `root[:inversion][:recipe]`
  (e.g. `C::maj7` for C major seventh, or `C:1:maj7` in first inversion).
- Slash and pedal bass: append `/bass` to a colon token (e.g. `G::maj/C` for G
  major over a C bass), enabling pedals such as `E/A`.

### Percussion system
- Pattern-based drums with fills and interrupters.
- Staged evolution: percussion that develops over time along a fill-rate curve.
- Humanized velocity and timing for a more natural performance.
- A library of pre-configured patterns for common styles.

### Musical styles
- Classical counterpoint with suspensions and anticipations.
- Jazz with extended chords, chromatic mediants, and complex progressions.
- Rock and metal driving rhythms with blast beats and fills.
- Funk pocket grooves with syncopation.
- Latin patterns including salsa and bossa nova clave.
- Ambient arpeggiated textures.

## Quick start

### 1. Set up the environment
```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
# development extras (tests, linting):
venv/bin/pip install -r requirements-dev.txt
```
Audio rendering additionally requires FluidSynth and ffmpeg:
```bash
brew install fluidsynth ffmpeg   # macOS
```

### 2. Generate music (MIDI only)
```bash
venv/bin/python music_generator.py --mode ostinato \
  --keys 'C::maj7, A::min9, D::min7, G::13' \
  --out my_song --no-play
```

### 3. Render audio
```bash
./play_music --save-wav --sf2 SoundFonts/arachno.sf2 \
  --keys 'C::maj7, A::min7, F::maj9, G::13' --out my_song
```

Output is written to `output/midi/<slug>/`, `output/audio/<slug>/`, and
`output/metadata/<slug>/`.

## Usage examples

### Basic generation
```bash
venv/bin/python music_generator.py \
  --mode complete \
  --chords sevenths \
  --satb-style counterpoint \
  --seconds 120 \
  --instrument jazzguitar \
  --out jazz_counterpoint --no-play
```

### Staged percussion
```bash
venv/bin/python music_generator.py \
  --seconds 180 \
  --perc-lib library/percussion_library.json \
  --perc-stages "32:rock:4/4:fast" "32:rock:4/4:halftime" \
  --perc-fill-curve "0.1:0.4" \
  --out progressive_rock --no-play
```

### Custom chord progressions
```bash
venv/bin/python music_generator.py \
  --keys "C:1:maj7, G:2:min7, A:0:min7, F:1:maj9" \
  --mode ostinato \
  --seconds 90 \
  --out custom_progression --no-play
```

## Configuration

### Instruments
```bash
--instrument piano
--instrument strings
--instrument jazzguitar
--instrument 73        # any GM program (0-127); 73 is flute
```

#### Dense voicing
SATB voicing uses four voices and discards tones from large chords.
`--voicing dense` instead sounds every chord tone, spread across the register, so
full elevenths and thirteenths, quartal stacks, clusters, and exotic sets
(`mystic`, `messiaen_*`, `petrushka`, `whole_tone`) ring out complete.

```bash
venv/bin/python music_generator.py --mode ostinato \
  --keys 'C::maj9, A::min11, F::maj7#11, G::13, E::mystic, Db::messiaen_resonance' \
  --voicing dense --instrument strings --chord-length w --out colors --no-play
```
Dense voicing uses a single timbre (`--instrument`); pair it with the chord
vocabulary in `library/chord_recipes.py`.

#### Per-voice instruments
By default all four SATB voices share one patch (`--instrument`). With split
stems (on by default) each voice is on its own channel, so any voice can take its
own instrument, most usefully a dedicated bass patch:

```bash
--instrument epiano --voice-instrument bass=33
--instrument strings --voice-instrument bass=bass --voice-instrument soprano=saw
```
Voices: `soprano`, `alto`, `tenor`, `bass`. Names accept aliases or GM numbers.
Requires split stems (disabled by `--no-split-stems`).

#### Bass lines
By default the bass voice tracks the SATB voicing (`--bass-style follow`).
Switch it to an independent line generated from the chord roots:

```bash
--bass-style octaves --bass-step 0.5   # root/octave bounce in eighths
--bass-style walking --bass-step 1.0   # quarter-note walking line with approach tones
```
Styles: `follow`, `root`, `octaves`, `fifths`, `walking`, `arp`. `--bass-step`
is the subdivision in beats. Honors slash and pedal basses, and pairs well with a
dedicated bass patch (`--voice-instrument bass=33`). Requires split stems.

### Velocity modes
```bash
--velocity-mode-chords human --velocity-mode-drums human   # humanized
--velocity-mode-chords random                              # random dynamics
--velocity-mode-chords uniform                             # uniform (default)
```

### SATB styles
```bash
--satb-style block                                  # block chords (default)
--satb-style counterpoint --counterpoint-step 0.25  # counterpoint lines
--satb-style arpeggio --counterpoint-step 0.125     # arpeggiated patterns
```

## Demo library

Press the demo button. `cook_song.py` is one catalog over two kinds of demo:

- **Songs** — full multi-section arrangements in `songs/*.yml` (the "press demo"
  tunes). The flagship is **Kiss On My List**.
- **Presets** — capability showcases in `library/song_cookbook.py` that demo the
  things a song file can't: fugue, process music, dense/exotic voicing, melody
  transforms, and evolving percussion.

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
`riders_on_the_storm`, `whiter_shade_of_pale`, `yesterday`. Several carry a real
melody line (scale-degree grammar) on top of the arrangement.

Presets: `dense_colors`, `counterpoint`, `fugue`, `process_additive`,
`process_additive_long` (~8 min), `process_phase`, `process_phase_5min`,
`process_phase_20min`, `melody_transforms`, `perc_evolution`, `salsa`, `rock`,
`rnb`, `bach_prelude`, `bach_counterpoint`.

A browser-playable gallery (rendered MIDI, no SoundFont needed) lives in
[`site/`](site/index.html) — regenerate it with `make gallery`.

To **edit every parameter live and hear it** — chords, voicing, bass, melody,
percussion tokens, process, seed, … — run the web editor (`make webapp`, then
`cd webapp/frontend && npm install && npm run dev`); it builds its controls from
the engine's own schema, so it always exposes the full feature set. See
[`webapp/README.md`](webapp/README.md).

Add your own preset to `library/song_cookbook.py`:

```python
"my_style": {
    "title": "My Custom Style",
    "description": "A unique musical approach",
    "args": ["--chords", "extended-chords", "--satb-style", "counterpoint"],
}
```

## Arrangements (song files)

For long-form pieces that evolve rather than loop, describe a song as a YAML
file: global `defaults` plus an ordered list of `sections`. Each section
overrides only what changes (chords, length via `repeat` or `bars`, tempo,
instruments, bass style, percussion density) and the sections play end to end.

```bash
venv/bin/python music_generator.py --song songs/kiss.yml --out kiss --no-play
# or render to audio:
./play_music --save-wav --no-play --song songs/kiss.yml --out kiss \
  --sf2 SoundFonts/arachno.sf2 --fx lush --normalize --boost-normalize 2
```

See [songs/kiss.yml](songs/kiss.yml) for a worked example and
[docs/design-notes/arrangement-plan.md](docs/design-notes/arrangement-plan.md) for the design.

## Fugue (experimental)

Generate a fugal exposition from a melodic subject expressed in the scale-degree
[melody grammar](docs/reference/token-grammar.md). Voices enter one at a time with the
subject (tonic) and answer (dominant, the subject up a fifth); the prior voice
continues with the countersubject, and a cadence closes the exposition.

```bash
venv/bin/python music_generator.py --fugue --instrument organ \
  --melody-key D --melody-mode minor --out fugue --no-play

./play_music --save-wav --no-play --fugue 'q1 q5 e4 e3 e2 e1 q7, q2 h1' \
  --instrument harpsi --melody-key C --melody-mode major \
  --sf2 SoundFonts/arachno.sf2 --fx lush --normalize --boost-normalize 2 --out fugue
```

This is an exposition only; episodes, middle entries in related keys, and
stretto and inversion devices are future work. It is built on the melody
primitive (`melody.py`): the answer is `transpose_diatonic(subject, 4)` and the
default countersubject is `invert(subject)`.

## Process music (experimental)

Minimalist process pieces from a single melodic cell (scale-degree
[grammar](docs/reference/token-grammar.md)), unfolding by rule:

- `phase` (Reich, *Piano Phase*): two voices loop the cell; the follower advances
  one note per stage, sweeping every alignment back to unison.
- `additive` (Glass): the cell grows a note at a time (1, 12, 123, ...) then
  contracts.
- `augment` (Reich, *Four Organs*): the cell's durations lengthen each stage.

```bash
./play_music --save-wav --no-play --process phase \
  --process-cell 's1 s2 s3 s5 s6 s5 s3 s2' --instrument 12 --bpm 160 \
  --melody-key E --melody-mode minor --sf2 SoundFonts/arachno.sf2 --out phase

venv/bin/python music_generator.py --process additive \
  --process-cell 'e1 e2 e3 e5 e7 e5 e3 e2' \
  --instrument organ --melody-key C --out additive --no-play
```

Tunables: `--process-cell`, `--process-reps` (stage length), `--process-stages`
(augment). Built on the melody primitive (`process.py`).

## Audio rendering

```bash
# render and play through a SoundFont
venv/bin/python music_generator.py --seconds 60 --out my_song \
  --sf2 SoundFonts/arachno.sf2

# MIDI only, no audio
venv/bin/python music_generator.py --seconds 60 --out my_song --no-play
```

## Library files

- `library/percussion_library.json`: drum-pattern definitions, GM percussion
  mappings, and style-specific patterns.
- `library/chord_recipes.py`: custom chord definitions, extended harmony, and
  inversion support.
- `library/keys_presets.json`: pre-configured key progressions, circle-of-fifths
  sequences, and modal progressions.
- `library/song_cookbook.py`: pre-configured song recipes for `cook_song.py`.

## Project structure

```
music-generator/
  music_generator.py     # CLI + orchestration; re-exports the engine below
  mtheory.py             # note/pitch tables, key parsing, chord recipes (base layer)
  tokens.py              # chord token DSL (colon chords, repetition, key expansion)
  percussion.py          # drum map, percussion DSL, drum timelines
  voicing.py             # SATB / dense / bass / arpeggio / counterpoint voicing
  midiout.py             # MidiOut — the mido-backed MIDI writer
  composition.py         # progressions, chord families, harmony timelines
  render.py              # audio rendering pipeline (FluidSynth, ffmpeg, metadata)
  play_music             # thin shim over render.py
  cook_song.py           # demo library CLI (songs + presets, gallery batch)
  arrangement.py         # YAML song-file arrangements
  fugue.py               # fugal exposition generator
  process.py             # minimalist process music
  melody.py              # scale-degree melody primitive
  library/               # chord recipes, percussion, presets, cookbook
  songs/                 # YAML song files
  docs/                  # architecture, grammar, and design notes
  tests/                 # pytest suite (token DSL and render smoke tests)
  output/                # generated MIDI, audio, and metadata (gitignored)
```

## Song catalog

Every render appends an entry to `output/master_catalog.json` (generation args,
timestamps, and output paths). Query it with `query_catalog.py`:

```bash
venv/bin/python query_catalog.py list [limit]   # recent songs (default 10)
venv/bin/python query_catalog.py search <query> # match keys/name/instrument/out
venv/bin/python query_catalog.py show <name>    # full details for one song
venv/bin/python query_catalog.py stats          # totals, instruments, BPM range
```

The catalog lives under the gitignored `output/`, so it's local to your machine.

## Development

A `Makefile` wraps the common tasks (all using the `./venv` interpreter):

```bash
make install   # create venv + install runtime and dev dependencies
make test      # run the pytest suite
make lint      # ruff check (config in pyproject.toml)
make format    # apply ruff's safe autofixes
make check     # lint + test — run before committing
```

The token DSL is pinned by `tests/test_tokens.py`, and `tests/test_integration.py`
exercises every render mode end to end. Run `make check` before and after any change,
and update [docs/reference/token-grammar.md](docs/reference/token-grammar.md) when the grammar changes.
See [docs/how-to/set-up-for-development.md](docs/how-to/set-up-for-development.md) for the full dev walkthrough.

## Documentation

[**docs/index.md**](docs/index.md) is the documentation home, organized by the
[Diátaxis](https://diataxis.fr/) framework (Tutorials · How-to · Reference ·
Explanation).

- [docs/explanation/architecture.md](docs/explanation/architecture.md): module map,
  layering, and data flow — start here.
- [docs/reference/token-grammar.md](docs/reference/token-grammar.md): the chord,
  percussion, and melody mini-languages.
- [docs/explanation/](docs/explanation/): how harmony and percussion work, and the
  design decisions behind the notation.
- [docs/design-notes/](docs/design-notes/): forward-looking plans (refactor,
  roadmap, arrangement, melody, lead-sheet import).

## Tips

- Use `--velocity-mode-chords human` for more realistic dynamics.
- Combine `--satb-style counterpoint` with `--counterpoint-step 0.25` for a
  classical feel.
- Layer chord families, e.g. `--chords triads sevenths ninths`.
- Use `--mode ostinato` for repetitive grooves and `--mode complete` for
  longer-form pieces.
- For audio, prefer high-quality SoundFonts and tune `--gain`; `--reverb 1
  --chorus 1` gives a richer sound.

## License

Released under the MIT License. See [LICENSE](LICENSE).
