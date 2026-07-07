# Architecture

*Explanation — the module map, dependency layering, and data flow. Read this first
to know where code lives.*

## The one-paragraph picture

The system is a **pipeline from text to sound**. A small family of **token
notations** (chords, percussion, melody) is parsed into musical structures;
a **harmony/voicing engine** turns chord tokens into voice-led SATB parts; a
**percussion engine** turns drum tokens into hits; these are assembled into a
timeline of **MIDI events** and written to a `.mid` file. An optional **render**
step turns MIDI into normalized audio via FluidSynth + ffmpeg. Several **modes**
(ostinato, arrangement, fugue, process) sit on top of the same core.

```
                       ┌─────────────── modes ───────────────┐
  token DSL            │ ostinato · arrangement · fugue ·     │
  (chords/perc/melody) │ process · mixed/complete             │
        │              └──────────────────┬───────────────────┘
        ▼                                 ▼
   parse tokens  ──►  harmony + voicing  ──►  event timeline  ──►  MIDI file
        │            percussion engine          (notes, hits)          │
        │            melody / transforms                               │
        ▼                                                              ▼
   (CLI or API)                                           render.py: FluidSynth
                                                          → WAV → ffmpeg → audio
```

## Module map

The core is a **layered set of engine modules** with a thin CLI/orchestration
shell on top, surrounded by **satellites**. Within the core, a module imports
only modules *above* it in the layering (no cycles). `music_generator.py`
re-exports every public name (star imports), so callers that reach through
`music_generator` (`mg.build_harmony_events`, etc.) keep working.

### Core (layered engine)

| Module | Responsibility | Depends on |
|---|---|---|
| **`mtheory.py`** | Note/pitch-class tables, duration + GM instrument maps, voice ranges + channels, `ChordDef`, key parsing, register helpers, chord-recipe loader. | — (base layer) |
| **`theory.py`** | Pitch-class set analysis for the chord recipes: normal/prime form, interval-class vector, Forte number, consonance rating, character flags (symmetry, quartal, whole-tone/octatonic subsets). Feeds `chord_reference.py`'s generated reference; distinct from `mtheory.py` (which is note/instrument plumbing, not set theory). | mtheory |
| **`percussion.py`** | Active drum map (load/set/get), the percussion-token DSL, `PercHit`/`PercStage`/`PercPlan`, grid quantisation, drum timelines, `build_perc_from_args`. | mtheory |
| **`tokens.py`** | Chord DSL: `parse_colon_key_token`, `*N`/`[...]*N` repetition, `key_roots` expansion. | mtheory |
| **`voicing.py`** | `realize_SATB`, `realize_dense`, `build_bass_line`, `build_arpeggio_events`, `build_counterpoint_lines` + voice-leading helpers. | mtheory |
| **`midiout.py`** | The `MidiOut` writer — mido-backed Type-1 serializer with stem splitting, humanisation, drum/chord scheduling. | mtheory, percussion |
| **`composition.py`** | `build_progression` + chord-family pickers, `build_chord_timeline`, `build_dense_timeline`, `build_harmony_events`. | mtheory, tokens, voicing |
| **`music_generator.py`** | CLI/`main`, manifest + master catalog, `render_events`/`resolve_out_path`/`_apply_melody`, project paths; re-exports all of the above. | everything above |
| **`logging_config.py`** | Centralized logging used across the core. | — |

Key entry points:

| Concern | Function | Location |
|---|---|---|
| chord token → `ChordDef` | `parse_colon_key_token` | [tokens.py:20](https://github.com/galenspikes/music-generator/blob/main/tokens.py) |
| operator expansion (`*N`) | `parse_repetition_token` / `parse_chain_repetition` | [tokens.py:92](https://github.com/galenspikes/music-generator/blob/main/tokens.py) |
| percussion token → hits | `parse_single_token` | [percussion.py:162](https://github.com/galenspikes/music-generator/blob/main/percussion.py) |
| interrupter substitution | `choose_perc_pattern` | [percussion.py:152](https://github.com/galenspikes/music-generator/blob/main/percussion.py) |
| SATB voicing | `realize_SATB` | [voicing.py:449](https://github.com/galenspikes/music-generator/blob/main/voicing.py) |
| soprano voice-leading | `pick_soprano` | [voicing.py:397](https://github.com/galenspikes/music-generator/blob/main/voicing.py) |
| chord event timeline | `build_chord_timeline` | [composition.py:334](https://github.com/galenspikes/music-generator/blob/main/composition.py) |
| MIDI serialization | `MidiOut` | [midiout.py](https://github.com/galenspikes/music-generator/blob/main/midiout.py) |

### Satellites (each depends on the core)
- **`melody.py`** → core. The scale-degree melody mini-language, its model, and the
  fugal transforms (invert / retrograde / augment).
- **`arrangement.py`** → core. The arrangement layer: a *song* is global settings
  plus an ordered list of *sections*, each rendered through the core and
  concatenated into one evolving piece. Driven by YAML song files (`songs/*.yml`).
- **`fugue.py`** → `melody` + core. The fugue generator (v1: exposition + cadence)
  on the four SATB voice-channels.
- **`process.py`** → `melody` + core. Process-music generator: phasing, additive,
  and augmentation applied to a melodic cell.
- **`generator_api.py`** → core. The **programmatic API seam** — the in-process
  entry point the web UI and tests build on, sharing one render path with the CLI.
- **`leadsheet.py`** → mtheory. Lead-sheet import's deterministic core: `chordsym_to_token`
  maps conventional chord symbols ("Cmaj7", "F#m7b5") to the colon-token DSL; `ir_to_song_yml`
  turns a normalized chart IR into an `arrangement.py`-ready `song.yml`. See
  [docs/design-notes/leadsheet-import-plan.md](../design-notes/leadsheet-import-plan.md).
- **`leadsheet_extract.py`** → `leadsheet`. Deterministic text-layer PDF extraction
  (`pdfplumber` words → IR chart): clusters words into lines, classifies chords vs.
  section labels, splits on barlines. Feeds `leadsheet.ir_to_song_yml`; see
  [how-to/import-a-lead-sheet.md](../how-to/import-a-lead-sheet.md).

### Audio + tooling
- **`render.py`** — wrapper (Python port of the old `play_music` zsh script).
  Pipeline: `music_generator.py → FluidSynth (WAV) → ffmpeg (loudnorm/boost) → play`.
  Consumes wrapper flags (`--sf2`, `--fx`, `--normalize`, `--boost-db`,
  `--save-wav`, …) and forwards the rest to the generator.
- **`cook_song.py`** — convenience CLI for rendering curated song recipes.
- **`query_catalog.py`** — query the master catalog of generated songs
  (`output/master_catalog.json`, written by each render).
- **`chord_reference.py`** — generates the chord-recipe reference: reads
  `library/chord_recipes.py`, analyses every recipe with `theory.py`, and writes
  `site/chords.html` (interactive explorer) and
  [docs/reference/chord-recipes.md](../reference/chord-recipes.md) (footnoted table).
  Run via `python chord_reference.py` or `make chords`.

### Web instrument
- **`webapp/backend/`** (FastAPI: `app.py`, `engine.py`) — wraps `generator_api`
  to serve generation over HTTP.
- **`webapp/frontend/`** (React + Vite: `App.jsx`, `HarmonyEditor.jsx`,
  `PercEditor.jsx`, `controls.jsx`) — the instrument UI. Also ships a Pyodide PWA
  path that runs the engine in-browser.
- **`webapp/chords-frontend/`** (React + Vite) — **ChordBuilder**, a separate,
  installable (PWA) instrument focused purely on chord progressions: a
  tap-driven builder (no typing tokens), per-chord Strike/Sustain/Arpeggio/Loop
  playback, client-side soundfont audition, and a saved-progression library.
  Its own Vite project, sharing `webapp/shared/` and the same backend, mounted
  at `/chords`. See [how-to/use-chordbuilder.md](../how-to/use-chordbuilder.md).

## Dependency layering (the rule)

Inside the core, imports flow strictly upward through the engine layers:

```
mtheory                              (base: no local deps)
   ▲     ▲       ▲        ▲
tokens percussion voicing │
   ▲     ▲       ▲        │
   │   midiout   │        │
   └─────┴───────┴──► composition
                          ▲
                   music_generator     (CLI shell; re-exports the engine)
                          ▲
      ┌───────────────────┼───────────────────┐
   melody           arrangement          generator_api
      ▲                                        ▲
  fugue, process                        webapp backend ──► webapp frontend
```

**Two invariants:**
1. *Within the core*, a module imports only layers above it — `mtheory` at the
   base, `composition` near the top, `music_generator` on top. No cycles.
2. *Across the boundary*, satellites may import the core; the core must never
   import a satellite.

Keep it that way — it's what lets each layer be tested and reasoned about in
isolation.

## Data flow, in detail

1. **Input.** Tokens arrive via the CLI (`--keys`, `--perc-main`, `--melody`, …),
   a YAML song file (arrangement mode), or the API (`generator_api`, used by the web UI).
   A song file can itself originate from a lead-sheet PDF:
   `leadsheet_extract.py` → chart IR → `leadsheet.py`'s `ir_to_song_yml` → `song.yml`
   → `arrangement.py`. See [how-to/import-a-lead-sheet.md](../how-to/import-a-lead-sheet.md).
2. **Parse.** Chord colon-tokens → chord definitions (root, pitch classes, bass);
   percussion tokens → timed hits with per-hit modifiers; melody → scale degrees.
   The `*N` / `[...]*N` operators expand first. See
   [reference/token-grammar.md](../reference/token-grammar.md).
3. **Realize harmony.** Each chord is voiced into SATB with voice-leading that
   minimizes motion and avoids static repetition. See
   [how-harmony-works.md](how-harmony-works.md).
4. **Realize percussion.** The main pattern plays each cycle unless an
   **interrupter** is substituted (probability `fill_rate`); per-hit `prob`/`flam`/`vel`
   modifiers apply. See [how-percussion-works.md](how-percussion-works.md).
5. **Assemble.** Voices, percussion, and any melody/lead are merged into one event
   timeline sized to `--seconds` (or the section/song length).
6. **Write MIDI.** The timeline is written to `output/midi/<slug>/…`.
7. **Render (optional).** `render.py` runs FluidSynth to WAV, then ffmpeg for
   loudness normalization / boost. Output lands under `output/{midi,audio,metadata}/<slug>/`.

## Modes (where they plug in)

All modes ultimately produce a core event timeline; they differ in *how the
material is chosen*:

- **ostinato** — `--keys` is the looped progression (token grammar applies).
- **mixed / complete** — the engine walks a circle-of-fifths default and picks
  chord qualities from `--chords` (ignores `--keys`).
- **arrangement** — a YAML song sequences multiple sections, each a core render.
- **fugue** — `fugue.py` builds an exposition from a melodic subject.
- **process** — `process.py` applies phasing/additive/augmentation to a cell.

## See also

- [The token system](token-system-report.md) — what the notation is and where it
  came from.
- [Design decisions (ADRs)](decisions/index.md) — *why* the notation is shaped this way.
- [Refactor plan](../design-notes/refactor-plan.md) — the code-health plan; the
  monolith break-up (Tier 3) that produced the layered modules above is complete.
