# ADR-0002: Named chord recipes (vs. fixed quality families)

- **Status:** Accepted
- **Date:** 2025-09-16

## Context

The first colon-token proposal ([ADR-0001](0001-colon-chord-tokens.md)) let the
`:recipe` slot select from a small fixed set of *quality families* —
`triads`, `sevenths`, `ninths`, `extended-chords`, `quartal`, `sus`, `add6`,
`lyd-dom`. That covers common cases but caps expressivity: a composer can't ask for
a specific exotic voicing without adding a new family in code.

## Decision

Make `:recipe` name an entry in an **open, extensible recipe library**
(`library/chord_recipes.py`), where each recipe is just a list of semitone offsets
from the root (`maj = [0,4,7]`, `maj7 = [0,4,7,11]`, …). Adding a chord type is
adding a data entry, not touching the parser. Default recipe: `min` if the root
ends in `m`, else `maj`.

## Rationale

In the 2025-09-16 session the fixed-family design was explicitly rejected in favor
of naming exact chords — the stated want was to "pass in information to tell the
generator exactly what kind of chord to generate," with examples like
`C:0:add7add9add13` and `Eb:2:hdim7`. The driving principle: **the notation should
express the composer's precise harmonic intent, and new harmony should not require
new code.**

Modeling a recipe as a bare list of intervals (rather than a class or rule) is what
makes inversion composable: inversion is defined as "the Nth interval of the recipe,
mod its length" ([code](../architecture.md)), which works for a 3-note triad or a
7-note chord without special-casing.

Alternatives considered:
- **Fixed quality families** — the rejected status quo; not extensible.
- **Interval lists inline in the token** (`C:(0,4,7,11)`) — maximally flexible but
  unreadable and verbose; named recipes give the readability with an escape hatch.

## Prior art

Chord dictionaries / vocabularies are universal — every chord library has one. This
is **not novel**. The only mildly distinctive angle is treating the recipe name as
the token's quality field so that arbitrary voicings are first-class without parser
changes; that's a sensible design, not an invention.

## Consequences

- **Enables** broad harmonic range (81 recipes today) and painless growth.
- **Enables** clean inversion semantics via the "Nth recipe-tone mod length" rule.
- **Cost:** recipe names are an API surface — renaming or removing one breaks
  existing charts. The catalog ([reference/chord-recipes.md](../../reference/chord-recipes.md))
  is generated from the library to stay truthful.

## Status / follow-ups

Accepted. The recipe set has been stable since the first commit. Future work could
allow inline interval lists as an escape hatch for one-off voicings.
