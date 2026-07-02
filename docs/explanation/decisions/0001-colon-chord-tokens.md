# ADR-0001: Colon-delimited chord tokens

- **Status:** Accepted
- **Date:** 2025-09-16

## Context

Early versions accepted chords as bare roots (`C, F, Ab`) with quality chosen
globally by a `--chords` family pool (triads / sevenths / ninths). This made it
impossible to control a *single* chord precisely — its quality, its inversion, or a
non-root bass — from inside the progression string. Transcribing real songs needs
exactly that per-chord control.

## Decision

Represent each chord as a single colon-delimited token:

```
root[:inversion][:recipe][/bass]
```

e.g. `C::maj7`, `Bb:1:min7`, `G::maj/C`. Empty middle sections are legal
(`A::maj9`, `Am::`), so the separator structure is stable even when fields are
omitted.

## Rationale

The shape was chosen (in the 2025-09-16 design session) for one reason: a single
positional, colon-delimited string can carry *several independent dimensions* of a
chord — root, inversion, quality, bass — while staying short enough to type inline
in a progression. Colons are unambiguous to split on and read naturally as
"slots."

Alternatives considered and rejected:
- **Bare roots + global quality pool** — the status quo; no per-chord control.
- **Slash notation only** (`C/E`) — handles bass but not quality or inversion.
- **A `--random-inversions` flag with weights** — was proposed during the session
  and explicitly set aside as "going too far into the weeds"; it solved variety,
  not *control*.

## Prior art (be honest about this)

This syntax is **nearly identical to Harte notation** — the de facto academic
standard for text chord annotation (Harte et al., *Symbolic Representation of
Musical Chords*, ISMIR 2005), which uses `root:shorthand(degrees)/bass`
(e.g. `C:maj7`, `C:maj7/3`). The colon notation here was arrived at independently,
but it is **not novel**. The defensible distinction is one of *purpose*: Harte's
syntax is **descriptive** (labeling chords already present in audio, for analysis),
whereas this is **generative/imperative** — the token is an instruction to
synthesize a voiced chord (with recipe-driven voicing, inversion-as-recipe-tone,
and pedal basses that need not be chord tones). Any external write-up must cite
Harte and frame the contribution as the generative reading, not the syntax.

## Consequences

- **Enables** precise, inline, per-chord control; composes cleanly with the recipe
  system ([ADR-0002](0002-named-chord-recipes.md)) and the `/bass` pedal
  ([ADR-0006](0006-interrupters.md) is unrelated; pedal bass arrived 2026-06-07).
- **Cost:** a custom parser to maintain (`parse_colon_key_token`), pinned by
  `tests/test_tokens.py`. The grammar must never drift silently.
- **Cost:** surface similarity to Harte invites "this already exists" unless the
  generative framing is made explicit up front.

## Status / follow-ups

Accepted and shipped. The slash `/bass` suffix was a later extension (2026-06-07),
forced by a real transcription; see the token grammar reference for current syntax.
