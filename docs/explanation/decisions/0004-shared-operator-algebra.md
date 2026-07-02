# ADR-0004: One shared operator algebra across the sub-languages

- **Status:** Accepted
- **Date:** 2025-10 *(exact date unrecorded; see provenance note)*

## Context

Long charts are tedious and error-prone to write out hit-by-hit or chord-by-chord
(a 32-bar pedal section is 32 identical tokens). The three notations — chords,
percussion, melody — each face the same repetition problem.

## Decision

Provide two repetition operators, used **identically across all three
sub-languages**:

- `token*N` — repeat one token N times (`C::maj7*4`, `qb*8`).
- `[a,b,c]*N` — repeat a group; inner tokens may carry their own `*N`
  (`[C,G]*2` → `C,G,C,G`).

So `G:1:sus2add6*32` is a 32-bar pedal section in one token.

## Rationale

The point is *uniformity*: one compression mechanism, orthogonal to the vocabulary,
applied the same way to harmony, rhythm, and melody. That orthogonality — a single
operator algebra layered over three different primitive sets — is what makes the
three parsers feel like **one language** rather than three. It is also the most
"language-design" decision in the project: good DSLs separate combinators from
atoms, and this does.

Alternatives considered:
- **Writing tokens out longhand** — the status quo; verbose and unreadable.
- **Per-language repeat syntaxes** — would have worked but forfeited the
  "one language" coherence that is the system's main aesthetic claim.

## Prior art

Repetition operators are common — TidalCycles uses `*` for repetition/speed
(`"bd*4"`), regex has `{N}`, music has repeat signs. The operators themselves are
**not novel**. The only interesting (and weak) angle is the cross-language
uniformity; even that is a tasteful design choice, not an invention.

## Provenance note (honesty)

As with [ADR-0003](0003-probability-in-the-token.md), **no contemporaneous design
record survives** — the operators are absent from the September 2025 conversations
(where repetition was done by hand, e.g. "repeat each root 16×") and present by the
first commit (2025-10-11). They were authored directly. This is significant: the
*unification* layer — the very thing that turns three parsers into one notation —
carries no AI-assistance fingerprints and was the author's own work. Rationale here
is reconstructed from structure.

## Consequences

- **Enables** compact charts and is the strongest support for the "it's one
  language, not three parsers" framing.
- **Cost:** the operators must be expanded consistently *before* every sub-language
  parses; an inconsistency would fork the grammar. Pinned by `tests/test_tokens.py`.

## Status / follow-ups

Accepted. This is the cleanest "system-level" claim the project has; lead with it in
any write-up about the notation's design.
