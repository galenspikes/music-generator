# ADR-0007: No progression generation — voice leading is the engine's intelligence

- **Status:** Accepted
- **Date:** 2026-07-08

## Context

Generative harmony systems conventionally spend their intelligence on *which
chords come next* — functional-harmony rules (I→IV→V→I walks, secondary
dominants, cadence targeting), Markov models over corpora, or ML generation.
This engine's root selection is deliberately simple by comparison: `--keys` is
honored verbatim (the chart *is* the progression), `--random-roots` shuffles a
circle of fifths, `--full-progression` walks the roots once. External reviews
and future contributors will recurrently read this as a gap and propose adding
a progression generator. This ADR exists to make the refusal durable.

## Decision

Progression *choice* is permanently out of scope for the engine's musical
intelligence. The user is either **deliberate** (colon tokens express exact
harmonic intent, per [ADR-0001](0001-colon-chord-tokens.md)/[0002](0002-named-chord-recipes.md))
or **embraces honest randomness** (a shuffle, not a fake-smart chooser). The
engine's intelligence is spent entirely on *realization*: voice leading,
voicing, register, and rhythm. Do not add functional-harmony generation,
cadence-aware progression pickers, or corpus-trained chord suggestion to the
engine.

## Rationale

Dated, first-person (2026-07-08 review session, paraphrased — not a verbatim
quote): the author's stated intent is that the user either chooses chords
deliberately or wants genuinely randomized progressions; generating
conventional cadential sequences was explicitly rejected as producing bland
output, and voice leading was named as the tool's central intelligence.

The structural argument: a progression generator competes with the token DSL —
the project's core asset — for the role of "where harmonic intent comes from,"
and its typical output (well-formed, bland cadential sequences) is exactly the
wallpaper the tool exists to avoid. Keeping root selection dumb also keeps
randomness honest: a shuffled circle of fifths claims nothing it doesn't do.

Alternatives considered:
- **Rules-based functional generation** — rejected as above: bland output,
  competes with the DSL.
- **Corpus/ML progression models** — rejected; also breaks the project's
  determinism/reproducibility ethos (seeded shuffles are reproducible; model
  inference pipelines rot).

## Prior art

Band-in-a-Box, iReal Pro, and most "AI song generators" sit on the other side
of this line (the system supplies the progression). Tools this project actually
resembles — engravers, trackers, live-coding languages — also refuse to choose
chords for the user. The refusal is not novel; *stating it* is the point.

## Consequences

- **Enables** the DSL to remain the single source of harmonic intent, and the
  voicing engine ([how-harmony-works](../how-harmony-works.md)) to remain the
  differentiator.
- **Guards** against well-meaning contributions that would reposition the tool.
- **Cost:** users who want "give me a nice progression" get a shuffle, not a
  composer. That is the product.
- Progression-*adjacent* helpers that don't choose chords (e.g. chart import,
  which maps intent someone else wrote — see
  [leadsheet-import-plan](../../design-notes/leadsheet-import-plan.md)) remain
  in scope.

## Status / follow-ups

Accepted. To change this, write a superseding ADR — do not add a generator
"experimentally."
