# Tutorial 2 — Your first song

*A guided lesson: turn a single looping groove into a multi-section piece that
develops. Builds on [Tutorial 1](01-first-groove.md).*

## Why sections

A single `--keys` loop is a groove. A *song* is several sections that share
material but **change texture** — that's what makes it evolve instead of repeat.
Songs are written as YAML files and run with `--song`.

## 1. Start from a worked example

Render one of the included songs and listen:

```bash
venv/bin/python music_generator.py --song songs/autumn_leaves.yml --out al --no-play
```

Open `songs/autumn_leaves.yml` and read it alongside the output.

## 2. Write your own

Create `songs/my_first_song.yml`:

```yaml
title: My First Song
tempo: 100
soundfont: SoundFonts/your.sf2

defaults:
  instrument: epiano
  satb: arpeggio
  chord_length: h
  perc:
    main: "qb, eg, qc, eg, qb, eg, qc, eg"
    fill_rate: 0.08

sections:
  - name: intro
    repeat: 1
    perc: { fill_rate: 0.02 }          # sparse
    keys: "C::maj9, A::min11"

  - name: verse
    repeat: 2
    keys: "C::maj9, A::min11, F::maj7, G::7"

  - name: lift
    repeat: 2
    instrument: saw                    # brighter timbre
    satb: block
    perc: { fill_rate: 0.22 }          # busier
    keys: "F::maj7, G::7, C::maj9, C::maj9"

  - name: outro
    repeat: 1
    perc: { fill_rate: 0.01 }          # settle
    keys: "C::maj9, C::maj9"
```

## 3. Render it

```bash
venv/bin/python music_generator.py --song songs/my_first_song.yml --out my_first_song --no-play
# or with audio:
./play_music --save-wav --sf2 SoundFonts/your.sf2 --song songs/my_first_song.yml --out my_first_song
```

## The lesson

Notice the four sections share chords but differ in **instrument, `satb` style, and
`perc.fill_rate`**. That contrast — sparse intro, fuller verse, bright busy lift,
settling outro — is the arrangement doing the developmental work that a single loop
can't. Keep harmony familiar; vary the texture.

**Next:** [Tutorial 3 — From idea to EP](03-from-idea-to-ep.md).
