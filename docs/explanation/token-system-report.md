# The Token System — a working report

*Status: draft / teaching document. The normative grammar is `docs/reference/token-grammar.md`;
this report explains the system, its design, and where it sits in the wider field.*

---

## 0. One-sentence claim

The project defines a small family of **text notations for music** — chords,
percussion, and melody — that share one **operator algebra** (`*N` repetition and
`[...]*N` grouping), and whose primitives encode not just *notes* but *generative
intent* (voicing recipes, hit probability, flams, transforms). The same written
artifact is both a **score** (readable, editable, diffable) and a set of
**instructions to a generator** that produces a family of renderings.

---

## 1. What the system actually is

Three sub-languages over a shared spine:

### 1a. Chord notation — `root[:inversion][:recipe][/bass]`
Parsed by `parse_colon_key_token` in `music_generator.py`.
- `root` — note name (`C`, `Eb`, `F#`, `Am`); sharps normalized to flats.
- `:inversion` — integer N; bass becomes the Nth recipe-tone (mod recipe length).
- `:recipe` — a named chord shape from `library/chord_recipes.py` (`maj7`, `quartal`,
  `sus4add7`, …). Defaults to `min` if the root ends in `m`, else `maj`.
- `/bass` — an explicit bass pitch class, **any note**, not just a chord tone
  (pedals, slash chords). An explicit `/bass` overrides the inversion.

Distinctive design decisions (these are *yours*, not universal convention):
- Inversion is defined as "the Nth tone of the recipe, mod its length" — so it
  composes correctly with arbitrary recipes, not just triads.
- The slash bass is decoupled from chord membership, so `G::maj/C` (C is not in
  the chord) is a first-class pedal, not an error.
- Empty colon sections are legal (`A::maj9`, `Am::`) — the separator structure is
  stable even when fields are omitted.

### 1b. Percussion notation — `<duration><instrument-letters>[modifiers]`
- duration letters `w h q e s t` (whole → 32nd).
- one or more instrument letters = simultaneous hits; `r` = rest.
- per-hit modifiers in `[...]`: `vel±N`, `probX` (stochastic!), `flamX` (grace hit).

Distinctive decision: **probability and flam live inside the note token.** The
notation is *generative at the primitive level* — ` qb[prob0.5]` is not a note,
it's a 50%-chance note. Most notations describe a fixed result; this one describes
a distribution.

### 1c. Melody notation — scale degrees
Parsed by `parse_melody` in `melody.py`. `<dur>[.]<accidental?><1-7><octave marks>`,
key/mode inferred from the chords. Built-in `invert`/`retrograde`/`augment`
transforms (the fugal operations) operate on the parsed line.

Distinctive decision: melody is written in **scale degrees, not absolute pitches**,
so the same line is portable across keys and can be anchored either to the section
key or re-anchored to each chord's root.

### 1d. The shared spine — operator algebra
Parsed by `parse_repetition_token` / `parse_chain_repetition`.
- `token*N` — repeat one token.
- `[a,b,c]*N` — repeat a group; inner tokens may carry their own `*N`.

This is the part that makes it a *system* rather than three parsers. The same
compression algebra works across all three notations: `G:1:sus2add6*32` writes a
32-bar pedal section as one token.

---

## 2. Provenance & development history

*Source: `docs/sources/genesis-dossier.md` (forensic reconstruction, 2026-06-18).
This section reports only what dated artifacts establish. Inferences and
interpretation are confined to §2.4 and clearly marked.*

### 2.1 What this repo's git can and cannot testify to
This repository's git history begins **2026-06-07**, but that is the *extraction*
date, not the invention date. The token system was built earlier, in a standalone
folder that was later folded into a monorepo ("spatelier"). **The genesis predates
all version control we have.** Claims about the original design intent are therefore
bounded by file mtimes and the first surviving commit, not by a continuous record.

### 2.2 Verified timeline (oldest → newest)
- **2025-09-13** — Harmony/SATB experiments. Hard-coded Python; **no token DSL**.
- **2025-09-14** — `independent_parts.py`: first composable CLI; **percussion
  letter-tokens exist, chords are still bare roots**. (Rhythm notation predates
  harmony notation.)
- **2025-09-15 → 2025-09-20** — The colon chord token is invented in this window:
  bare roots on the 15th; `--keys "G::7, C::7"` in `play_blues.sh` by the 20th.
  Exact day unrecoverable.
- **2025-10-11** — First git commit anywhere (spatelier monorepo "Initial commit").
  Already contains the **complete** system: `parse_colon_key_token`, the full
  chord-recipe library, percussion `prob`/`flam`/`vel` modifiers, and both `*N`
  operators.
  The recipe library has gained no new recipes since.
- **2026-06-07** — Extracted into this standalone repo. Same day, three genuinely
  new additions: **(a)** `/bass` slash/pedal support — driven by the *Kiss On My
  List* transcription; **(b)** the **freeze**: test suite (`tests/test_tokens.py`)
  + normative grammar (`docs/token-grammar.md`); **(c)** the **melody** scale-degree
  language (`melody.py`) — no earlier copy exists.

### 2.3 Original motivation (verbatim, 2025-09 scratch notes)
> generative music... i would like to release some of these in an album or EP.
> def want: billie jean, mathrock_blues_A, superstition

The system was built to make generative versions of real songs for a record. The
notation served that goal; it was not designed top-down from a specification.

### 2.4 Surviving design rationale — and its limits
Contemporaneous "why" documentation is **largely absent**. No design memo or chat
log explaining the colon syntax, the in-token `prob`/`flam`, or the `*N` operator
was recovered. Their rationale is *inferable from structure only* — treat any such
explanation as reconstruction, not testimony.

The **one** exception with real provenance is the melody language: `docs/melody-
primitive-plan.md` (2026-06-07) explicitly weighs absolute notes vs. intervals vs.
scale degrees and chooses degrees with stated reasons ("inversion is a reflection
of degrees about an axis; augmentation scales durations — all key-independent").
This is the only documented, dated, self-authored design decision in the corpus.

> **Caution for any external presentation:** do not cite this report's earlier
> drafts as a "source" for design rationale. Speculative interpretation written
> here must not be laundered back into evidence. Keep *artifact says* and
> *author infers* strictly separate.

---

## 3. Related work (to be expanded)

- **Live-coding pattern DSLs** — TidalCycles (Alex McLean), Strudel, Sonic Pi,
  FoxDot. Closest cousins; differ in that they target ephemeral live pattern,
  this targets durable song/arrangement structure.
- **Grammar-based harmony** — Mark Steedman, *A Generative Grammar for Jazz Chord
  Sequences* (1984). Direct ancestor of a rule-based chord notation.
- **Notation/representation** — LilyPond, ABC, MusicXML; the TENOR conference.
- **The seam** — Thor Magnusson, *Sonic Writing* (2019): code as musical
  inscription, score-as-instrument.

---

## 4. Annotated reading list (to be written)

Each entry: the work, why it matters *to this project*, and what to take from it.
TODO: Magnusson, Steedman, McLean (TidalCycles PhD), Tymoczko, Nierhaus, Roads.
