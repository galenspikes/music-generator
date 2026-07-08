# ADR-0008: Pitch-class sets as substrate, named recipes as surface

- **Status:** Accepted
- **Date:** 2026-07-08

## Context

A harmony engine must pick a chord representation, and the two established
poles both have known failure modes. **Spelled-pitch models** (music21's
Note/Pitch objects: letter + accidental + octave) preserve enharmonic meaning
but pay for it structurally — inversions, slash basses, and exotic qualities
each need special-casing on top of the spelled representation. **Set-theoretic
interfaces** (AthenaCL, where the harmonic vocabulary is literally the Forte
catalog and users type `4-27`) get perfect composability but are unusable as a
pop-facing notation.

## Decision

Split substrate from surface. The engine's chord representation is an
**unordered pitch-class set** plus a root and optional bass
(`ChordDef(root_pc, pcs, bass_pc)` in `mtheory.py`); the grammar exposes
**pop-facing recipe names** (`maj7`, `hdim7`, `sus2add6` — [ADR-0002](0002-named-chord-recipes.md)).
Set theory is implementation, never interface. Ordering, register, and octave
are re-derived downstream by the voicing layer (`realize_SATB` and friends),
which is where they belong.

## Rationale

Partly dated, first-person (2026-07-08 review session, paraphrased — not a
verbatim quote): the author identifies the DSL's design influences as Unix and
regex conventions, pitch-class set theory, and a bias toward pop music forms —
set theory as a stated influence, pop forms as the stated surface bias. The
composability argument below is **reconstructed** from the design's structure,
and says so.

Because a chord is a set, the grammar's orthogonal slots compose without
special cases: a recipe is offsets reduced to a set, inversion is "Nth
recipe-tone mod length" picking a bass, a slash bass is one field that may lie
outside the set entirely (`G::maj/C`), and any recipe × inversion × bass
combination just works. `theory.py`'s analysis layer (prime form, interval
vectors, Forte numbers) reads the same sets to generate the chord reference —
analysis and generation share one substrate.

Alternatives considered:
- **Spelled pitches** — rejected implicitly by the parser itself: sharps
  normalize to flats (`C# → Db`), so the engine never had enharmonic
  distinctions to preserve. Correct for a MIDI-first tool; MIDI has no
  spelling.
- **Sets as the user vocabulary** (the AthenaCL position) — composing pop by
  Forte number; rejected by the surface bias above.

## Prior art

Reducing chords to pitch-class sets internally is common in MIDI-era tools and
is **not novel**. AthenaCL made sets the *interface* and stayed academic;
music21 kept spelled pitches and treats set analysis as a view. Tymoczko's
voice-leading geometry (*A Geometry of Music*) is the theoretical statement of
this architecture — chords as unordered sets, voice leading as minimal paths —
arrived at here independently. The distinctive angle is only the deliberate
substrate/surface split: Forte underneath, Nashville on top.

## Consequences

- **Enables** free composition of recipe/inversion/bass (no special cases),
  and one representation serving both generation and `chord_reference.py`'s
  analysis.
- **Enables** the voicing layer's independence: sets in, voiced notes out —
  the seam the whole engine layering rests on.
- **Cost:** no enharmonic spelling anywhere — `C#`/`Db` are one pitch class,
  and notation-facing exports (e.g. a future MusicXML path) would need a
  spelling pass bolted on.
- **Cost:** duplicate recipe pcs (e.g. `hdim7`/`m7b5`) are indistinguishable
  downstream of the parser; labels live only in `ChordDef.label`.

## Status / follow-ups

Accepted (documenting long-standing practice). If a notation export ever
lands, spelling becomes its problem, not `ChordDef`'s.
