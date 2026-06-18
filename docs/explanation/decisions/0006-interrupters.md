# ADR-0006: Interrupters — probabilistic pattern substitution

- **Status:** Accepted
- **Date:** 2025-09-13

## Context

A literally looping ostinato is monotonous; the 20-minute-groove goal needs
variation that stays recognizable. The need: inject fills and variations into an
otherwise repeating pattern, with a controllable amount.

## Decision

Define an **interrupter**: an alternative pattern that, each cycle, *replaces* the
main pattern with probability `fill_rate` (otherwise the main pattern plays):

```python
def choose_perc_pattern(main, interrupters, fill_rate):
    if interrupters and fill_rate > 0.0 and random.random() < fill_rate:
        return random.choice(interrupters)
    return main
```

Three flavors: **percussion interrupters** (`--perc-interrupters`, default rate
0.20), **chord interrupters** (`--chord-interrupters`, default 0.00 — rhythmic chord
motifs of `c`/`r` events), and the **main beat itself**, which shares the
interrupter format so there is no separate "main pattern" syntax.

## Rationale

From the 2025-09-13 design session: the percussion track should have "a 'main beat'
which takes the same format as an interrupter, and … an interrupter argument." Two
principles fall out:

1. **Substitution, not addition** — an interrupter *replaces* a slot rather than
   layering on top, so one die-roll per cycle suffices and the groove stays
   rhythmically coherent.
2. **One shared format** — main beat and interrupters use the same percussion token
   grammar, an early instance of the "one language" instinct later generalized in
   [ADR-0004](0004-shared-operator-algebra.md).

`fill_rate` is the knob with the clearest musical meaning: ~0.05 is hypnotic and
locked, ~0.4 is busy and restless.

## Prior art (be honest)

This is **probabilistic substitution from a fixed vocabulary** — a well-established
technique, **not novel**. Direct prior art: stochastic drum-machine fills, and
live-coding combinators like TidalCycles' `sometimes` / `degrade` / `wchoose`
(`sometimesBy 0.2 (# fill) pattern` is essentially this mechanism). Arrived at
independently from a musical instinct ("this is bland, go crazier"), but it must be
presented as being in that lineage, not as an invention.

## Consequences

- **Enables** controllable, recognizable variation over long spans — the core of
  the ostinato vision — and is *evidence* for the notation-as-instrument framing
  (a generative primitive expressed in the same notation you compose with).
- **Note:** combined with per-hit `prob` ([ADR-0003](0003-probability-in-the-token.md))
  there are two tiers of randomness (phrase-level vs. hit-level); name them as a
  pair in any explanation.
- **Limitation:** substitution gives *non-repetition*, not *musical development* —
  it avoids exact loops but does not create an arc. Long-form narrative remains an
  open problem (see roadmap).

## Status / follow-ups

Accepted. The honest framing — "stochastic fills, in the live-coding lineage,
integrated into the notation" — is what to use externally.
