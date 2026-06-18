# How to create an arrangement

*Goal: sequence multiple sections into one evolving piece with a YAML song file.
When `--song` is set, section-based rendering is used and most other flags are
ignored.*

## Render a song

```bash
venv/bin/python music_generator.py --song songs/autumn_leaves.yml --out autumn --no-play
```

## The song file

A *song* is global settings + `defaults` + an ordered list of `sections`. Each
section overrides the defaults and supplies its own `keys`:

```yaml
title: Autumn Leaves
tempo: 116
soundfont: SoundFonts/arachno.sf2

defaults:                      # applied to every section unless overridden
  instrument: epiano
  voices: { bass: 32 }         # per-voice GM program
  bass: { style: walking, step: 0.5 }
  satb: arpeggio
  chord_length: h
  perc:
    main: "er,eg,er,eg, er,eg,er,ei"
    fill_rate: 0.08

sections:
  - name: head
    repeat: 2                  # play this section twice
    keys: "A::min7, D::7, G::maj7, C::maj7"

  - name: solo
    repeat: 2
    instrument: saw            # override just for this section
    perc: { fill_rate: 0.18 }  # busier fills in the solo
    keys: "A::min7, D::7, G::maj7, C::maj7"

  - name: outro
    satb: block
    perc: { fill_rate: 0.02 }  # settle down
    keys: "A::min7, D::7, G::min, G::min"
```

## The pattern

The arrangement layer is where the *evolution* lives: keep `keys` similar across
sections but **change the texture** — instrument, `satb` style, `bass` style, and
especially `perc.fill_rate` — so the piece develops rather than just loops. Use the
existing files in `songs/` as worked templates.

## See also
[arrangement design note](../design-notes/arrangement-plan.md) ·
[Kiss On My List song study](../explanation/song-studies/kiss-on-my-list.md)
