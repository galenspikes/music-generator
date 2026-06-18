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

The codebase is a **core monolith with satellites**. Everything depends on
`music_generator.py`; nothing in the core depends back on the satellites.

### Core
- **`music_generator.py`** — the heart. Token parsing (chord colon-tokens,
  percussion tokens, the `*N`/`[...]*N` operators), the harmony model, SATB
  voicing and voice-leading (`pick_soprano`), the percussion engine
  (hits, modifiers, interrupters), the event timeline, MIDI writing, and the CLI
  (`main`). Depends only on `logging_config`. *(This is the monolith the refactor
  plan aims to break up — see [design-notes/refactor-plan.md](../design-notes/refactor-plan.md).)*
- **`logging_config.py`** — centralized logging used across the core.

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

### Audio + tooling
- **`render.py`** — wrapper (Python port of the old `play_music` zsh script).
  Pipeline: `music_generator.py → FluidSynth (WAV) → ffmpeg (loudnorm/boost) → play`.
  Consumes wrapper flags (`--sf2`, `--fx`, `--normalize`, `--boost-db`,
  `--save-wav`, …) and forwards the rest to the generator.
- **`cook_song.py`** — convenience CLI for rendering curated song recipes.
- **`cleanup_audio.py`, `recreate_audio.py`, `query_catalog.py`** — housekeeping
  utilities (prune WAVs, re-render audio from existing MIDI, query the song catalog).

### Web instrument
- **`webapp/backend/`** (FastAPI: `app.py`, `engine.py`) — wraps `generator_api`
  to serve generation over HTTP.
- **`webapp/frontend/`** (React + Vite: `App.jsx`, `HarmonyEditor.jsx`,
  `PercEditor.jsx`, `controls.jsx`) — the instrument UI. Also ships a Pyodide PWA
  path that runs the engine in-browser.

## Dependency layering (the rule)

```
logging_config
      ▲
music_generator  ◄──────────────┐  (core; depends on nothing local but logging)
      ▲         ▲        ▲       │
   melody   arrangement  generator_api
      ▲                        ▲
  fugue, process          webapp backend ──► webapp frontend
```

**The invariant:** dependencies point *toward* the core. A satellite may import the
core; the core must never import a satellite. Keep it that way — it's what lets the
core be tested and reasoned about in isolation, and what the refactor plan preserves.

## Data flow, in detail

1. **Input.** Tokens arrive via the CLI (`--keys`, `--perc-main`, `--melody`, …),
   a YAML song file (arrangement mode), or the API (`generator_api`, used by the web UI).
2. **Parse.** Chord colon-tokens → chord definitions (root, pitch classes, bass);
   percussion tokens → timed hits with per-hit modifiers; melody → scale degrees.
   The `*N` / `[...]*N` operators expand first. See
   [reference/token-grammar.md](../reference/token-grammar.md).
3. **Realize harmony.** Each chord is voiced into SATB with voice-leading that
   minimizes motion and avoids static repetition. See
   [how-harmony-works.md](how-harmony-works.md) *(planned)*.
4. **Realize percussion.** The main pattern plays each cycle unless an
   **interrupter** is substituted (probability `fill_rate`); per-hit `prob`/`flam`/`vel`
   modifiers apply. See [how-percussion-works.md](how-percussion-works.md) *(planned)*.
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
- [Design decisions (ADRs)](decisions/) — *why* the notation is shaped this way.
- [Refactor plan](../design-notes/refactor-plan.md) — the active plan to break up
  the `music_generator.py` monolith.
