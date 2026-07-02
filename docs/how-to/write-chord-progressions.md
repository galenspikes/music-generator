# How to write chord progressions

*Goal: drive harmony from `--keys` in ostinato mode. Assumes you've read the
[token grammar](../reference/token-grammar.md) basics.*

## Basic progression

In `ostinato` mode, `--keys` **is** the progression, looped to fill `--seconds`:

```bash
venv/bin/python music_generator.py --mode ostinato \
  --keys "C::maj7, A::min7, D::min7, G::7" \
  --seconds 60 --out my_progression --no-play
```

## Control each chord precisely

Use the colon token `root[:inversion][:recipe][/bass]`:

```bash
# quality via recipe (see reference/chord-recipes.md for all 81)
--keys "C::maj9, F::13, Bb::min11, Eb::quartal"

# inversions (bass = Nth recipe tone)
--keys "C::maj7, C:1:maj7, C:2:maj7"

# slash / pedal bass (bass need not be a chord tone)
--keys "G::maj/C, F::7/Eb, Am::min/E"
```

## Repeat compactly

```bash
# hold one chord for 32 bars
--keys "G:1:sus2add6*32"

# repeat a group
--keys "[C::maj7, A::min7]*4"
```

## Tips

- **No colon = bare root.** `--keys "C, G, Am"` lets quality come from `--chords`.
- **Chord rhythm:** `--chord-length {w,h,q,e,s,t}` sets how long each chord lasts.
- **Rhythmic chords:** add `--chord-interrupters` + `--chord-fill-rate` to break
  sustained chords into stabs (see [how percussion works](../explanation/how-percussion-works.md)).
- **Voicing style:** `--satb-style {block,counterpoint,arpeggio}` or
  `--voicing dense` to sound every tone. See
  [how harmony works](../explanation/how-harmony-works.md).

## See also
[ADR-0001 (colon tokens)](../explanation/decisions/0001-colon-chord-tokens.md) ·
[chord-recipe catalog](../reference/chord-recipes.md)
