# ADR-0003: Probability and articulation inside the percussion token

- **Status:** Accepted
- **Date:** 2025-10 *(exact date unrecorded; see provenance note)*

## Context

A looping percussion pattern played literally is robotic. Two kinds of variation
were wanted: human micro-feel (a hit slightly louder, a grace-note flam) and
controlled non-determinism (a hit that fires only *sometimes*). The question was
*where* to express these — as global CLI flags, or per-hit in the notation.

## Decision

Attach per-hit modifiers directly to a percussion token in brackets:

```
<duration><letters>[vel±N,probX,flamX]
```

e.g. `qb[vel+10,prob0.5,flam0.1]` — a quarter kick, +10 velocity, 50% chance to
sound, with a grace hit 0.1 beats later. The modifier lives on the *note*, not on a
global flag.

## Rationale

Putting probability and articulation **inside the primitive** makes a single
written pattern describe a *distribution* of performances rather than one fixed
performance. `qb[prob0.5]` is not a note — it's a coin flip. This is the most
"generative" feature of the notation and the cleanest way to get per-hit, locally
scoped variation that a global "humanize" flag cannot express (different hits want
different probabilities and feels).

Alternatives considered:
- **Global CLI flags** (`--humanize`, `--swing`, a single fill probability) — these
  *did* exist in the September 2025 prototype and were kept for coarse control, but
  they can't vary hit-by-hit.
- **A separate per-hit data table** — more flexible but divorces the variation from
  the pattern you're reading; in-token keeps intent and data together.

## Prior art

Per-event probability and velocity are standard in live-coding pattern languages —
TidalCycles expresses probability with `?` and has per-event controls; drum
machines have had probabilistic fills for decades. Flams/grace notes are ordinary
notation. This is an independent re-derivation, **not novel**; the only design
choice that is "ours" is the specific in-token packaging.

## Provenance note (honesty)

Unlike [ADR-0001](0001-colon-chord-tokens.md)/[ADR-0002](0002-named-chord-recipes.md),
**no contemporaneous design discussion survives for this decision.** The feature is
absent from the September 2025 design conversations and present by the first commit
(2025-10-11); it was authored directly, outside any recorded design session. The
rationale above is therefore *reconstructed from the design's structure*, not quoted
from a dated source — treat it as such.

## Consequences

- **Enables** distribution-valued patterns and per-hit human feel.
- **Creates two layers of randomness** — this per-hit `prob` and the phrase-level
  interrupter `fill_rate` ([ADR-0006](0006-interrupters.md)). They compose but are
  conceptually distinct (micro- vs. phrase-variation); document them as a pair.
- **Cost:** parser and renderer complexity; non-determinism makes output
  non-reproducible unless the RNG is seeded — pass `--seed N` for a repeatable take.

## Status / follow-ups

Accepted. Reproducibility is covered by the existing `--seed` flag.
