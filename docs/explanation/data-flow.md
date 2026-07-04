# Data flow in detail

*Explanation — a single trace of how input becomes sound, with the real code
touchpoints. The high-level version is in [architecture.md](architecture.md); this
is the step-by-step. File references point into `music_generator.py`.*

## The pipeline

```
input ─► expand operators ─► parse ─► realize ─► assemble ─► write MIDI ─► render
(CLI/API/YAML)   *N           tokens   harmony+    event       .mid file    FluidSynth
                              → defs    percussion  timeline                 → ffmpeg
```

Each stage is pure-ish and hands a concrete structure to the next; nothing
downstream reaches back. That's what makes the engine testable in pieces.

## A worked trace

Follow `--keys "C::maj9, A::min11"` with `--perc-main "ebg, er"`:

### 1. Input
Tokens arrive from the CLI (`--keys`, `--perc-main`), a YAML song (`--song`,
[arrangement.py](https://github.com/galenspikes/music-generator/blob/main/arrangement.py)), or the API
([generator_api.py](https://github.com/galenspikes/music-generator/blob/main/generator_api.py), used by the web UI). All three funnel
into the same core.

### 2. Expand operators
`*N` and `[...]*N` are expanded **first**, before any sub-language parses
(`parse_repetition_token` / `parse_chain_repetition`,
[music_generator.py:1369](https://github.com/galenspikes/music-generator/blob/main/music_generator.py)). `[C,G]*2` becomes
`C,G,C,G`. After this step the engine only sees flat token lists.

### 3. Parse to structures
Each sub-language has its own parser, all producing plain data:

- **Chords** → `ChordDef` via `parse_colon_key_token`
  ([music_generator.py:786](https://github.com/galenspikes/music-generator/blob/main/music_generator.py)).
  `C::maj9` → `root_pc=0`, `pcs=(0,2,4,7,11)` (C D E G B), `bass_pc=None`.
- **Percussion** → `(beats, [PercHit…])` via `parse_single_token`
  ([music_generator.py:1184](https://github.com/galenspikes/music-generator/blob/main/music_generator.py)).
  `ebg` → `(0.5, [PercHit(note=36), PercHit(note=42)])` — a kick and a closed hat
  together; `er` → `(0.5, [])`, an eighth rest.
- **Melody** (if `--melody`) → scale-degree notes via `parse_melody`
  ([melody.py](https://github.com/galenspikes/music-generator/blob/main/melody.py)).

At this point a chord is still just a set of pitch classes — no register, no voicing.

### 4. Realize
- **Harmony:** each `ChordDef` is voiced into SATB by `realize_SATB`
  ([music_generator.py:1538](https://github.com/galenspikes/music-generator/blob/main/music_generator.py)), which splits guide vs.
  color tones and calls `pick_soprano`
  ([music_generator.py:861](https://github.com/galenspikes/music-generator/blob/main/music_generator.py)) for a voice-led top line.
  `C::maj9` → bass C3, tenor E4, alto D4, soprano B3. See
  [how harmony works](how-harmony-works.md).
- **Percussion:** each cycle, `choose_perc_pattern`
  ([music_generator.py:1170](https://github.com/galenspikes/music-generator/blob/main/music_generator.py)) plays the main pattern or
  substitutes a fill with probability `fill_rate`. Per-hit `prob`/`flam`/`vel` apply
  to the chosen pattern. See [how percussion works](how-percussion-works.md).

### 5. Assemble the timeline
Voices, percussion, and any melody are merged into one ordered list of events
(`build_chord_timeline`, [music_generator.py:1746](https://github.com/galenspikes/music-generator/blob/main/music_generator.py), and
its percussion counterpart), sized to `--seconds` (or the section/song length). The
last chord sustains to fill any remainder.

### 6. Write MIDI
The event timeline is written to `output/midi/<slug>/…`. Stems are split by default
(`--split-stems`) so each voice/percussion part is separable. This `.mid` is the
engine's actual product — everything after is optional audio.

### 7. Render (optional)
[render.py](https://github.com/galenspikes/music-generator/blob/main/render.py) (or the `./play_music` shim) runs the MIDI through
FluidSynth (→ WAV) and ffmpeg (loudness normalize / boost), landing audio under
`output/audio/<slug>/`. See [how to render audio](../how-to/render-audio.md).

## Why this shape

The strict left-to-right flow — *parse to data, realize, assemble, emit* — is what
lets the token tests (`tests/test_tokens.py`) pin the parsers in isolation and the
integration tests exercise each mode end to end. It also keeps the modes (ostinato,
arrangement, fugue, process) as different *front ends* that all converge on the same
event-timeline → MIDI back end.

## See also
[Architecture](architecture.md) · [How harmony works](how-harmony-works.md) ·
[How percussion works](how-percussion-works.md)
