# Token grammar — formalization and expressive power

*A deep dive into the token DSL: what it can express, how to visualize it, and its capacity for representing "living musical ideas." The three token languages (chord, percussion, melody) form the interface between human intention and machine generation.*

## What lives here

- **[formalization.md](formalization.md)** — grammar specification, visual notation, recursive structure
- **[living-musical-ideas.md](living-musical-ideas.md)** — what constitutes a "living" musical idea in this system; examples; limits
- **[barber-fugue-study.md](barber-fugue-study.md)** — case study: can we represent (or approximate) the fugue from Barber's Piano Sonata Op. 26? What does it require? What would break?

## Current status

The token languages exist and work (the grammar is pinned by `tests/test_tokens.py`):
- **Chord tokens** (`--keys`) — bare roots or `root:inversion:recipe/bass` colon notation
- **Percussion tokens** (`--perc-main`, `--perc-interrupters`) — `duration + instrument-letters + modifiers`
- **Melody tokens** (`--melody`) — scale degrees with duration, octave marks, transforms

This folder formalizes, extends, and tests the expressive limits.

## See also

- [Reference token grammar](../reference/token-grammar.md) — the canonical spec (pinned by tests)
- [Melody primitive plan](../design-notes/melody-primitive-plan.md) — the design rationale for scale-degree representation
