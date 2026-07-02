# How to build percussion patterns

*Goal: write a groove with `--perc-main`, add fills with interrupters. See the
[percussion letter map](../reference/percussion-letters.md) for the drum alphabet.*

## A main beat

Tokens are `<duration><letters>[modifiers]`, comma-separated. Stacked letters
sound together; `r` is a rest.

```bash
venv/bin/python music_generator.py --mode ostinato \
  --keys "C::min9" --seconds 30 --out groove --no-play \
  --perc-main "qb, eg, qc, eg, qb, eg, qc, eg"
#            kick  hat snare hat ...
```

`ebg` = eighth kick **and** closed hat together; `er` = eighth rest.

## Add fills (interrupters)

Interrupters replace the main beat some of the time:

```bash
--perc-main "eg,eg,eg,eg,eg,eg,eg,eg" \
--perc-interrupters "qc,qc,sd,sd,qc" "eb,eb,qi" \
--perc-fill-rate 0.2
```

`--perc-fill-rate` is the variation knob: ~0.05 hypnotic, ~0.4 busy.

## Per-hit modifiers

Inside `[...]` after a letter:

```bash
# louder, 50% chance, with a flam
--perc-main "qb[vel+10], qg[prob0.5], qc[flam0.1], qg"
```

`[vel±N]` velocity, `[probX]` probability (0–1), `[flamX]` grace hit. This is the
per-hit *micro* tier of variation; interrupters are the *phrase* tier — see
[how percussion works](../explanation/how-percussion-works.md).

## Tips

- **Bar math:** in 4/4, eight `e` (eighth) tokens = one bar.
- **Humanize:** `--velocity-mode-drums human` for natural dynamics.
- **Intensity staging:** `--perc-stages` + `--perc-fill-curve` ramp fills over time.

## See also
[ADR-0006 (interrupters)](../explanation/decisions/0006-interrupters.md) ·
[percussion letter map](../reference/percussion-letters.md)
