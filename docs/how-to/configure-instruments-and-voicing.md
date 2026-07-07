# How to configure instruments and voicing

*Goal: pick timbres and shape how chords are voiced across the SATB voices —
per-voice patches, an independent bass line, velocity behaviour, and the
block/counterpoint/arpeggio/dense voicing styles.*

## Instruments

```bash
--instrument piano
--instrument strings
--instrument jazzguitar
--instrument 73        # any GM program (0-127); 73 is flute
```

By default all four SATB voices share one patch (`--instrument`).

## Per-voice instruments

With split stems (on by default) each voice is on its own channel, so any
voice can take its own instrument — most usefully a dedicated bass patch:

```bash
--instrument epiano --voice-instrument bass=33
--instrument strings --voice-instrument bass=bass --voice-instrument soprano=saw
```

Voices: `soprano`, `alto`, `tenor`, `bass`. Names accept aliases or GM
numbers. Voices not set fall back to `--instrument`. Requires split stems
(disabled by `--no-split-stems`).

## Bass lines

By default the bass voice tracks the SATB voicing (`--bass-style follow`).
Switch it to an independent line generated from the chord roots:

```bash
--bass-style octaves --bass-step 0.5   # root/octave bounce in eighths
--bass-style walking --bass-step 1.0   # quarter-note walking line with approach tones
```

Styles: `follow`, `none`, `root`, `octaves`, `fifths`, `walking`, `arp`.
`--bass-step` is the subdivision in beats. Honors slash and pedal basses, and
pairs well with a dedicated bass patch (`--voice-instrument bass=33`).
Requires split stems.

## Velocity modes

```bash
--velocity-mode-chords human --velocity-mode-drums human   # humanized
--velocity-mode-chords random                              # random dynamics
--velocity-mode-chords uniform                              # uniform (default)
```

## SATB styles

```bash
--satb-style block                                  # block chords (default)
--satb-style static                                 # freezes the voicing across an unchanged chord (no wobble)
--satb-style counterpoint --counterpoint-step 0.25  # counterpoint lines
--satb-style arpeggio --counterpoint-step 0.125     # arpeggiated patterns
```

`counterpoint`/`arpeggio` also take `--counterpoint-suspension-prob` and
`--counterpoint-anticipation-prob` (0–1) to add suspensions/anticipations per
voice at chord changes.

## Dense voicing

SATB voicing uses four voices and discards tones from large chords.
`--voicing dense` instead sounds every chord tone, spread across the
register, so full elevenths and thirteenths, quartal stacks, clusters, and
exotic sets (`mystic`, `messiaen_*`, `petrushka`, `whole_tone`) ring out
complete.

```bash
venv/bin/python music_generator.py --mode ostinato \
  --keys 'C::maj9, A::min11, F::maj7#11, G::13, E::mystic, Db::messiaen_resonance' \
  --voicing dense --instrument strings --chord-length w --out colors --no-play
```

Dense voicing uses a single timbre (`--instrument`); pair it with the chord
vocabulary in `library/chord_recipes.py` (see the
[chord recipe reference](../reference/chord-recipes.md)).

## See also

- [Write chord progressions](write-chord-progressions.md)
- [CLI reference](../reference/cli-reference.md)
