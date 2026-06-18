# ADR-0005: Scale degrees (not absolute pitches) for melody

- **Status:** Accepted
- **Date:** 2026-06-07

## Context

The melody primitive needed a written form for monophonic lines that would also
support the fugal operations (the *answer* = diatonic transposition, *inversion*,
*retrograde*, *augmentation*). The representation choice determines how clean those
operations are.

## Decision

Write melodies as **scale degrees** relative to a key + mode:
`q1 e2 e3 q5 | h2 q1 qr` (duration prefix, degree `1`–`7`, optional `#`/`b`,
`'`/`,` octave marks, `r` rest). The key/mode is inferred from the chords unless
overridden. Degrees may resolve against the section key or be re-anchored to each
chord's root.

## Rationale

This is the project's **best-documented design decision** — a contemporaneous design
memo (`docs/design-notes/melody-primitive-plan.md`, 2026-06-07) weighs three options
explicitly:

- **Absolute notes** (`C4 E4 G4`): simple but key-dependent; diatonic transposition
  (the fugal answer) and inversion are awkward.
- **Intervals** (relative steps): good for transpose, clumsy for inversion/retrograde
  and for reading.
- **Scale degrees** (`1 3 5`): **chosen** — every fugal operation is a clean
  transform on degrees (the answer is a diatonic shift; inversion is a reflection of
  degrees about an axis; augmentation scales durations — all key-independent).

The deciding principle: pick the representation in which the operations you need are
*trivial*. Degrees make the fugal transforms arithmetic.

## Prior art

Degree-based notation is old and common — the Nashville Number System (for chords),
movable-do solfège, and pitch-class numbering in set theory / serialism all encode
relative scale position. The fugal transforms are textbook counterpoint; `music21`
implements them. This is **not novel**; it is a well-reasoned application of a
standard idea, and the documented reasoning is its real value.

## Consequences

- **Enables** key-independent melodies and trivial fugal transforms; shares the
  `*N` operator algebra ([ADR-0004](0004-shared-operator-algebra.md)) and the
  duration grammar with the other sub-languages, reinforcing "one language."
- **Cost:** degrees are meaningless without a key/mode context, so the engine must
  infer or be told one; chromatic notes need accidentals (`#4`, `b7`).

## Status / follow-ups

Accepted. Shared foundation for the melody, lead/hook, and fugue generators.
