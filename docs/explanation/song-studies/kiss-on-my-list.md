# Kiss On My List (Hall & Oates) — the flagship demo

This is the star of the demo library — the song the "press demo" button plays
(`make demo`). It lives as a finished multi-section arrangement in
[`songs/kiss.yml`](../../../songs/kiss.yml) and renders to ~2.5 minutes at its
authored per-section tempo map.

Goal: a great-sounding, finished pop song that shows off the arrangement layer —
a real form with a dynamic arc, not a loop.

## Key decisions
- **Capo 3 → rendered at concert (sounding) pitch** (written shape +3 semitones),
  so it matches the record. Mapping used:

  | Written (capo shape) | Concert | Token |
  |---|---|---|
  | A    | C   | `C::maj` |
  | Am   | Cm  | `C::min` |
  | C    | Eb  | `Eb::maj` |
  | D    | F   | `F::maj` |
  | Dm   | Fm  | `F::min` |
  | Dm7  | Fm7 | `F::min7` |
  | Dm9  | Fm9 | `F::min9` |
  | E    | G   | `G::maj` |
  | E7   | G7  | `G::7` |
  | Esus/B | Gsus4 | `G::sus4` |
  | E7sus | G7sus4 | `G::sus4add7` |
  | F    | Ab  | `Ab::maj` |
  | G    | Bb  | `Bb::maj` |
  | Amaj7 | Cmaj7 | `C::maj7` |
  | Dmaj7 | Fmaj7 | `F::maj7` |
  | D7/C  | F7 (top) | `F::7` |
  | Bm7   | Dm7 | `D::min7` |
  | Bm7add11 | Dm7add11 | `D::min11` |

- **Slash chords** (E/A, D/A, G/A, D7/C, D/E, Esus/B): now rendered with a real
  pedal/slash bass via the `/bass` token suffix (e.g. `G::maj/C` = G major over a
  C bass). The chorus rides a concert-C pedal (= the written A-pedal under E/A,
  D/A, G/A). Bass need not be a chord tone.

## Current form (the arrangement in `songs/kiss.yml`)
Intro → Verse 1 → Pre-chorus 1 → Chorus 1 → Verse 2 → Pre-chorus 2 →
Chorus 2 → Solo → Breakdown → Final chorus → Outro.

The two cycles are deliberately not identical: **Pre-chorus 2 uses `D::min11`**
(the Bm7add11 colour) where Pre-chorus 1 stays on `F::min7`. The arc is carried
by texture, not just chords:

| Knob | Intro | Verses | Pre-choruses | Choruses | Solo | Breakdown | Outro |
|---|---|---|---|---|---|---|---|
| tempo | 140 | 148 | 148 | 150 | 152 | 146 | 146 |
| `satb` | block | arpeggio | arpeggio | arpeggio | arpeggio | block | arpeggio |
| `bass.style` | root | root | octaves | octaves | walking | root | octaves |
| lead (`soprano`) | — | — | — | saw | saw (main) | — | — |
| `perc.fill_rate` | 0.0 | 0.10–0.12 | 0.18–0.20 | 0.30–0.32 | 0.22 | 0.04 | 0.08 |

## Render command
```bash
# MIDI only
venv/bin/python music_generator.py --song songs/kiss.yml --out kiss --no-play

# Audio (needs a SoundFont) — the "press demo" experience is `make demo`
./play_music --save-wav --no-play --song songs/kiss.yml --out kiss \
  --sf2 SoundFonts/arachno.sf2 --fx lush --normalize --boost-normalize 2
```

> **Render tempos come from the YAML, not the CLI.** The arrangement path only
> overrides a song's `defaults` with a CLI flag you *actually pass* — so
> `--song songs/kiss.yml` renders at the authored per-section tempo map
> (140→152). Pass `--bpm N` to rescale the whole song proportionally.

> Slash-bass syntax: append `/bass` to any colon token — `root[:inv][:recipe]/bass`.
> The bass pitch class can be any note (not just chord tones), so pedals work.
> An explicit `/bass` overrides an inversion.

## Long-form variant (optional)
For a 10–20 min generative version, raise the `repeat:` counts on the verse/
chorus/solo sections (and/or add evolving copies with different `perc.fill_rate`
and chord interrupters) so the piece keeps developing rather than resolving to
the outro. The flagship intentionally stays radio-length for the demo button.

## Done
- ~~Add pedal-bass for the chorus slash chords~~ (`/bass` suffix).
- ~~Add the pre-chorus #2 variant with `D::min11`~~.
- ~~Vary sections so it evolves rather than looping identically~~ (fill-rate arc,
  breakdown, per-section tempo/bass/satb).
- ~~Port from the flat `--seconds` ostinato path to a real `--song` arrangement~~.
