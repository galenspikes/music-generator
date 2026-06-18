# The token system — overview & provenance

*Explanation. This doc covers two things you won't find elsewhere: the **synthesis
claim** (what the notation is, as a whole) and the **provenance** (where it came
from). For other angles, go to the right place:*

- *Syntax* → [reference/token-grammar.md](../reference/token-grammar.md)
- *Why each choice was made* → [design decisions (ADRs)](decisions/)
- *How it sits in the field + reading* → [music-theory-companion.md](music-theory-companion.md)

---

## The claim, in one sentence

The project defines a small family of **text notations for music** — chords,
percussion, and melody — that share one **operator algebra** (`*N` repetition and
`[...]*N` grouping), and whose primitives encode not just *notes* but *generative
intent* (voicing recipes, hit probability, flams, transforms). The same written
artifact is both a **score** (readable, editable, diffable) and a set of
**instructions to a generator** that produces a family of renderings.

That dual character — score *and* generative instruction, in one hand-writable
language — is the system-level idea. Every individual primitive is conventional
(see the [ADRs](decisions/) for honest prior art on each); the **synthesis** is the
contribution.

## What it is, at a glance

Three sub-languages over one shared spine:

- **Chords** — `root[:inversion][:recipe][/bass]`, recipe-driven voicing.
  ([ADR-0001](decisions/0001-colon-chord-tokens.md), [ADR-0002](decisions/0002-named-chord-recipes.md))
- **Percussion** — `<duration><letters>[modifiers]`, with `prob`/`flam`/`vel` riding
  on the individual hit. ([ADR-0003](decisions/0003-probability-in-the-token.md))
- **Melody** — scale degrees with fugal transforms.
  ([ADR-0005](decisions/0005-scale-degree-melody.md))
- **Shared spine** — the `*N` / `[...]*N` operator algebra, applied identically
  across all three. This is what makes it *one language* rather than three parsers.
  ([ADR-0004](decisions/0004-shared-operator-algebra.md))

For the full syntax see the [grammar reference](../reference/token-grammar.md); for
how it's realized into sound see [data-flow.md](data-flow.md).

## Provenance & development history

*This section reports only what dated artifacts establish. The fuller forensic
record is kept privately outside the repo; design rationale lives in the ADRs.*

### What this repo's git can and cannot testify to
This repository's git history begins **2026-06-07**, but that is the *extraction*
date, not the invention date. The token system was built earlier, in a standalone
folder later folded into a monorepo ("spatelier"). **The genesis predates all
version control we have** — claims about original intent are bounded by file mtimes
and the first surviving commit, not a continuous record.

### Verified timeline
- **2025-09-13** — Harmony/SATB experiments. Hard-coded Python; **no token DSL**.
- **2025-09-14** — first composable CLI; **percussion letter-tokens exist, chords
  are still bare roots** (rhythm notation predates harmony notation).
- **2025-09-15 → 09-20** — the colon chord token is invented in this window
  (bare roots on the 15th; `--keys "G::7, C::7"` by the 20th). Exact day unrecoverable.
- **2025-10-11** — first git commit anywhere already contains the **complete**
  system: the colon parser, the full recipe library, percussion `prob`/`flam`/`vel`,
  and both `*N` operators. The recipe library has gained none since.
- **2026-06-07** — extracted into this repo. Same day, three genuinely new additions:
  (a) `/bass` slash/pedal, driven by the *Kiss On My List* transcription; (b) the
  **freeze** — test suite + normative grammar; (c) the **melody** scale-degree
  language (no earlier copy exists).

### Original motivation (verbatim, 2025-09 notes)
> generative music… i would like to release some of these in an album or EP.

The system was built to make generative versions of real songs for a record. The
notation served that goal; it was **not** designed top-down from a specification.

### The limits of the rationale
Contemporaneous "why" documentation is **largely absent** — no design memo or log
explaining the colon syntax, the in-token `prob`/`flam`, or the `*N` operator
survives; their rationale is reconstructed from structure (and the ADRs say so).
The **one** documented exception is the melody language, whose design memo weighs
absolute notes vs. intervals vs. scale degrees with stated reasons. Notably, the
unification layer (the operator algebra) carries no AI-assistance fingerprints — it
was authored directly.

> **Honesty rule:** keep *artifact says* and *author infers* strictly separate. Do
> not cite reconstructed rationale as primary evidence.

## See also
[Architecture](architecture.md) · [Music-theory companion](music-theory-companion.md) ·
[Design decisions](decisions/)
