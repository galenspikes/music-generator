# Music Generator

A Python music-generation system built around a compact **token DSL** for
chords, percussion, and melody. The engine parses those tokens into harmony,
voice-led SATB parts, and drum hits; assembles them into a MIDI timeline; and
optionally renders audio through FluidSynth. On top of that core sit several
ways to work with it — a scriptable CLI, a browser instrument, a
progression-only PWA, and an arrangement layer for long-form songs.

The token DSL is the core of the project; the
[token grammar reference](docs/reference/token-grammar.md) documents it in
full, and [docs/explanation/architecture.md](docs/explanation/architecture.md)
maps how the modules fit together.

## The project, at a glance

| Piece | What it is | Where |
|---|---|---|
| **Engine** | The token DSL, harmony/voicing, percussion, and MIDI writer. Everything else builds on this. | `mtheory.py`, `tokens.py`, `voicing.py`, `percussion.py`, `composition.py`, `midiout.py` |
| **CLI** | Scriptable generation from the command line — every engine parameter as a flag. | `music_generator.py`; see the [CLI reference](docs/reference/cli-reference.md) and [how-to guides](docs/how-to/index.md) |
| **Web instrument** | A browser UI that builds its controls from the engine's own schema — edit chords, voicing, bass, melody, and percussion tokens live and hear the result. | [`webapp/`](webapp/) — see [`webapp/README.md`](webapp/README.md) |
| **ChordBuilder** | A separate, installable (PWA) instrument focused purely on chord progressions: tap-driven, no typing tokens or numbers, with per-chord Strike/Sustain/Arpeggio/Loop playback. | [`webapp/chords-frontend/`](webapp/chords-frontend/), mounted at `/chords`; see the [how-to guide](docs/how-to/use-chordbuilder.md) |
| **Arrangements** | YAML song files that sequence sections into an evolving long-form piece, instead of one looping groove. | `arrangement.py`, `songs/*.yml`; see the [how-to guide](docs/how-to/create-an-arrangement.md) |
| **Lead-sheet import** | Turn a chord chart PDF into a working `song.yml`. | `leadsheet.py`, `leadsheet_extract.py`; see [the how-to guide](docs/how-to/import-a-lead-sheet.md) |

**Live demo:** the web instrument is deployed as a Hugging Face Space via
[`Dockerfile`](Dockerfile) — see [`space/README.md`](space/README.md) for
deployment details. A static project showcase also lives in
[`site/`](site/) (served via GitHub Pages, and mirrored at `/showcase` on the
Space).

## Features

### Harmony generation
- Multiple chord families: triads, sevenths, ninths, extended chords, chromatic
  mediants, quartal harmony, suspended chords, lydian dominant.
- SATB voicing styles: block chords, counterpoint lines, arpeggiated patterns,
  and a dense mode that sounds every chord tone.
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

## Getting started

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

From here, pick a way in:
- **[Tutorial 1: your first groove](docs/tutorials/01-first-groove.md)** —
  the fastest path from a fresh clone to a playing groove.
- **`make demo`** — plays the flagship song (*Kiss On My List*); see
  [Explore the demo library](docs/how-to/explore-the-demo-library.md) for the
  full catalog.
- **The web instrument** — `make webapp`, then see
  [`webapp/README.md`](webapp/README.md) to run the frontend(s) locally.
- **[docs/how-to/](docs/how-to/index.md)** — task-oriented recipes for chord
  progressions, percussion, melodies, arrangements, instruments/voicing,
  and audio rendering.

Output from CLI generation lands in `output/{midi,audio,metadata}/<slug>/`
(gitignored).

## Project structure

```
music-generator/
  music_generator.py     # CLI + orchestration; re-exports the engine below
  mtheory.py              # note/pitch tables, key parsing, chord recipes (base layer)
  theory.py                # pitch-class set analysis (Forte numbers, prime forms) for chord_reference.py
  tokens.py               # chord token DSL (colon chords, repetition, key expansion)
  percussion.py           # drum map, percussion DSL, drum timelines
  voicing.py              # SATB / dense / bass / arpeggio / counterpoint voicing
  midiout.py              # MidiOut — the mido-backed MIDI writer
  composition.py          # progressions, chord families, harmony timelines
  generator_api.py        # in-process API seam shared by the CLI and webapp
  arrangement.py          # YAML song-file arrangements
  leadsheet.py             # lead-sheet chord-symbol -> token DSL, IR -> song.yml
  leadsheet_extract.py     # PDF -> chart IR extraction (text-layer PDFs)
  melody.py                # scale-degree melody primitive (song-file overlays)
  render.py                # audio rendering pipeline (FluidSynth, ffmpeg, metadata)
  play_music               # thin shim over render.py
  render_gallery.py         # batch-renders the demo gallery (site/assets/midi)
  chord_reference.py        # generates the chord-recipe reference docs/pages
  webapp/                   # web instrument (backend, frontend, ChordBuilder)
  space/                    # Hugging Face Space packaging (README, deploy notes)
  library/                  # chord recipes, percussion, key presets, cookbook
  songs/                    # YAML song files
  site/                     # static demo gallery / project showcase (GitHub Pages)
  docs/                     # architecture, grammar, how-to guides, design notes
  tests/                    # pytest suite (token DSL and render smoke tests)
  output/                   # generated MIDI, audio, and metadata (gitignored)
```

## Library files

- `library/percussion_library.json`: drum-pattern definitions, GM percussion
  mappings, and style-specific patterns.
- `library/chord_recipes.py`: custom chord definitions, extended harmony, and
  inversion support.
- `library/keys_presets.json`: pre-configured key progressions, circle-of-fifths
  sequences, and modal progressions.
- `library/song_cookbook.py`: pre-configured capability-preset recipes (`make gallery`,
  `docs/how-to/explore-the-demo-library.md`).

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
- [docs/how-to/](docs/how-to/index.md): recipes for every generation mode,
  the web instrument, and development setup.
- [docs/explanation/](docs/explanation/): how harmony and percussion work, and the
  design decisions behind the notation.
- [docs/design-notes/](docs/design-notes/): forward-looking plans (refactor,
  roadmap, arrangement, melody, lead-sheet import).

## License

Released under the MIT License. See [LICENSE](LICENSE).
