# Music-theory companion

*Explanation — where this project's ideas sit in the wider field, and what to read.
This is the honest "related work" map: for each area, the prior art, and what the
engine takes from it. Nothing here is claimed as novel; the value is in the
synthesis. See the [ADRs](decisions/) for per-decision prior-art notes.*

## Chord notation — Harte

The colon chord token (`C::maj7`, `G::maj/C`) is **nearly identical to Harte
notation** — the de facto academic standard for text chord annotation (Harte,
Sandler, Abdallah, Gómez, *Symbolic Representation of Musical Chords*, ISMIR 2005),
which uses `root:shorthand(degrees)/bass`. The honest framing: this was arrived at
independently but is **not novel** as syntax. The defensible distinction is
*purpose* — Harte's notation is **descriptive** (labeling chords in existing audio
for analysis); ours is **generative** (an instruction to synthesize a voiced
chord). → [PDF](http://ismir2005.ismir.net/proceedings/1080.pdf). See
[ADR-0001](decisions/0001-colon-chord-tokens.md).

## Voice-leading — Tymoczko, and jazz guide tones

The voicing engine chooses each chord's notes to **minimize motion from the previous
chord while favoring functionally important tones** ([how harmony works](how-harmony-works.md)).
Two lineages:

- **Dmitri Tymoczko, *A Geometry of Music* (Oxford, 2011)** — the formal account of
  voice-leading as short paths in chord space. The `pick_soprano` step-cost term is
  a heuristic shadow of this. → [author page](https://dmitri.mycpanel.princeton.edu/geometry-of-music.html).
- **Jazz guide-tone practice** — voicing around the 3rd and 7th (the notes that
  define quality), treating the 5th as disposable and the root as optional on
  extended chords. The engine's guide/color split is exactly this idea.

## Grammar-based harmony — Steedman

Representing chord progressions with a **generative grammar** has a direct ancestor:
**Mark Steedman, *A Generative Grammar for Jazz Chord Sequences* (Music Perception,
1984)** — rewrite rules that generate the 12-bar blues family. The token DSL is a
generative, rule-bearing notation in this lineage (recipes, operators), though it
targets *song/arrangement* structure rather than analysis.
→ [PDF](http://dub.ucsd.edu/Mu270d/Harmony/marc-steedman.pdf).

## The harmonic DNA — chromatic mediants & split thirds

The project's *sound* — its taste — came from a specific harmonic appetite visible
from the first day: **chromatic mediants** (root motion by thirds between major/minor
triads, the neo-Riemannian L/R/P transformations) and **split-third / blues chords**
(both the major and minor third). These aren't features so much as the composer's
ear. Neo-Riemannian theory (David Lewin, Richard Cohn; the *Tonnetz*) is the formal
language for the mediant relationships, and Tymoczko situates them geometrically.

## Rhythm & controlled variation — the live-coding lineage

The percussion token language, per-hit probability, and interrupters all live in the
world of **live-coding pattern DSLs**:

- **TidalCycles** (Alex McLean) — `*N` repetition (`"bd*4"`), per-event probability
  (`?`), and `sometimes`/`degrade` (probabilistic substitution = interrupters).
  → [tidalcycles.org](https://tidalcycles.org); McLean's PhD,
  [*Artist-Programmers…*](https://slab.org/about/) (Goldsmiths, 2011).
- Drum machines — stochastic fills predate all of it.

The engine's two-tier randomness (per-hit `[prob]` + per-cycle `fill_rate`) is an
independent re-derivation of these ideas, integrated into one notation.
See [ADR-0003](decisions/0003-probability-in-the-token.md) /
[ADR-0006](decisions/0006-interrupters.md).

## Process music — Reich & Glass

The `--process` mode (phasing, additive, augmentation) is **deliberate homage**, not
invention: Steve Reich's phasing, Philip Glass's additive process, and Reich's *Four
Organs* (augmentation). The `songs/four_organs.yml` piece is explicit about this.

## The field map — Nierhaus

For the overall landscape of automated composition (grammars, Markov chains,
stochastic methods, constraints), the single best survey is **Gerhard Nierhaus,
*Algorithmic Composition: Paradigms of Automated Music Generation* (Springer, 2008)**.
→ [Springer](https://link.springer.com/book/10.1007/978-3-211-75540-2).

## The seam — Magnusson

The project's most interesting *framing* claim — a hand-writable notation that is
*also* a live, long-form generative instrument — is theorized in **Thor Magnusson,
*Sonic Writing* (Bloomsbury, 2019)**: code as musical inscription, the score
becoming an instrument. This is the closest intellectual ally and the work to
position against. → [Google Books](https://books.google.com/books/about/Sonic_Writing.html?id=di5FwAEACAAJ).

## How to read this list

You don't need all of it. For fluency: **Magnusson** cover-to-cover (the framing),
**skim Harte** (so you can cite the prior art yourself), and **play TidalCycles for a
weekend** (the rhythm/variation lineage from experience). The rest is reference for
when you write the work up.

## See also
[The token system](token-system-report.md) · [Design decisions](decisions/) ·
[How harmony works](how-harmony-works.md)
