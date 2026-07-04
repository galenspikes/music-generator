# Stasis and function — the ground state, and why music is deviation from it

*Explanation — the aesthetic spine of the project: the **why behind the why**. The
other Explanation docs describe how harmony, percussion, and the tokens work. This
one says what they are all **for**. It is a statement of intent, and it is honest
about where the code does not yet live up to it.*

---

## The ground state — the project's "A 440"

Every measuring system needs a reference that is, in itself, featureless: the sine
wave, the tuning fork's A 440, the unweighted blank. This project has one too. When
you open the instrument and press **play** with nothing configured, the sound you
should hear is:

> **C major 7, root position, electric piano, straight eighth notes, 120 bpm — held,
> unchanging.**

That is not a boring default to be replaced as soon as possible. It is the
**reference signal**. It is *stasis* — home, rest, the rubber band at rest length.
It is deliberately the most consonant, most centered, most going-nowhere sound the
engine can make. Everything else is measured against it.

In engineering terms this ground state is exactly the [`vamp`
primitive](../design-notes/literal-mode-workflow-audit.md) — the *identity element*
the engine is missing: hold one literal chord, static voicing, straight
subdivisions, one instrument, no generation. The fact that the app could not, until
recently, even *produce* its own ground state is the clue that the philosophy was
implicit in the ear but not yet explicit in the code. **The aesthetic and the
engineering are the same fact seen from two sides:** the ground state is the vamp;
the vamp is the ground state.

A note on the chord. Home is `Cmaj7`, not a bare `C` triad, on purpose. The major
seventh is the **jazz tonic of rest** — the I chord that sounds finished without
sounding plain. And there is a quiet joke in it: the maj7 *contains its own leading
tone* (the B), the very note that, an octave's worth of context later, will want to
pull back to C. Home that holds a whisper of the pull homeward. Even the stasis is
faintly tensed.

---

## Music is what you do to the ground state

If the ground state is stasis, then **music is managed deviation from it.** Pull the
rubber band: the further from home, the more it strains to return. *Tension* is
distance from home; *release* is the return. A piece is a trajectory of departures
and homecomings — leave, wander, resolve.

This is not a metaphor the project decorates itself with after the fact. It is the
reason the code is shaped the way it is. The clearest tell is the name **interrupter**.

### Why "interrupters" are called interrupters

A percussion fill, a chord stab, a variation — the engine calls these
**interrupters** ([ADR-0006](decisions/0006-interrupters.md)), and the word is
load-bearing. The main pattern is *home*: the thing the groove wants to keep doing.
An interrupter **interrupts that homeward stasis** — it is the hand pulling the band.
And the knob that controls it, `fill_rate`, is therefore not "how many fills" but
**how hard and how often you pull**:

- `fill_rate ≈ 0.05` — barely tensed; hypnotic, locked, almost pure stasis.
- `fill_rate ≈ 0.4` — restless; the band is yanked constantly and never settles.

ADR-0006 honestly notes a limit: probabilistic substitution gives *non-repetition*,
not *development* — it avoids exact loops but does not shape an arc. This doc names
why that gap exists. **Development is a *shaped* trajectory of departure and return**
— pull further over here, resolve decisively over there. Random interruption pulls
the band by a random amount at random times; it deviates but does not *narrate*.
Closing that gap (a deviation budget that rises and falls with intent) is the
project's central open problem — see [roadmap](../design-notes/roadmap-phase2.md).

---

## The formal name for this is *functional harmony*

The idea that a sound is not just itself but has a **role relative to a home** is the
oldest organizing principle in Western tonal music, and it has a name: **functional
harmony**. Three functions, one cycle:

| Function | Role | The rubber band |
|---|---|---|
| **Tonic** (I) | home, rest, arrival | the band at rest |
| **Subdominant / Predominant** (IV, ii) | departure, the leaving | the first stretch |
| **Dominant** (V, V7) | maximum tension, *wants* to resolve | fully stretched, straining home |

The fundamental gesture **T → S → D → T** *is* the rubber band written as chords:
leave home, stretch, snap back. The engine of the pull is the **leading tone** — the
half-step below the tonic (B→C in our key) — and the tritone inside the dominant
(B–F in G7), the most unstable interval in the system, which resolves by contracting
to the tonic's third and root. Tonal music is, at bottom, the staging and release of
that one small dissonance.

Zoom all the way out and you reach the most radical version of the project's own
thesis. **Heinrich Schenker** argued that an entire tonal piece is nothing but the
**prolongation** — the elaboration over time — of a *single tonic triad*. The whole
sonata is the ground state, decorated. That is, almost word for word, *"music is
everything we do to that stasis."* When you say the Cmaj7 vamp is what the app
*is*, and a song is what you *do* to it, you are restating Schenker for a generator.

---

## How the engine encodes this — and where it doesn't (be honest)

| The idea | In the engine today | Honest status |
|---|---|---|
| ground state / tonic / home | the (planned) `vamp`; a held literal chord | **partly** — the engine couldn't render its own home until `vamp`; tracked in the [audit](../design-notes/literal-mode-workflow-audit.md) |
| deviation as a controllable force | `fill_rate`, interrupters, `--process` | **yes** — but the amount is *stochastic*, not *shaped* |
| tension = distance from home | — | **no** — there is no model of tonal distance; chords are picked from families ([ADR-0002](decisions/0002-named-chord-recipes.md)), not pulled toward a tonic |
| resolution / cadence | — | **no** — progressions do not currently *aim* anywhere; they cycle |

This is the important admission: **functional harmony is, right now, in the
composer's ear and in this document — not yet in the code.** The engine produces
sounds that *can* be used functionally, but it has no internal sense of "home,"
"away," or "the pull between them." There is no number for how stretched the band is.

That absence is the most promising direction the project has. Give the engine a
**model of tonal distance** — a computed tension that rises as harmony, register, and
density depart from the ground state, and a bias that lets it *resolve* — and three
things happen at once: the `vamp` becomes the formal definition of home; interrupters
gain a *budget* that can be shaped into an arc; and "development" stops being an open
problem. Lerdahl's *Tonal Pitch Space* (below) is very nearly a specification for
this. **The ground state is not the floor of the project. It is the origin of its
coordinate system.**

---

## Things to read

Curated, in rough reading order. The companion's [related-work
map](music-theory-companion.md#the-field-map-nierhaus) carries the full
bibliography; these are the ones that speak directly to *stasis, function, and
deviation*.

**The thesis itself — a piece is an elaborated home**
- **Heinrich Schenker, *Free Composition* (Der freie Satz, 1935).** The radical
  source for "the whole piece is the prolonged tonic." The most exact theoretical
  ally this project has. Hard going; start with a guide —
  **Allen Forte & Steven Gilbert, *Introduction to Schenkerian Analysis* (Norton,
  1982)**, or Tom Pankhurst's free *SchenkerGUIDE* (schenkerguide.com).

**Where the word "function" comes from**
- **Hugo Riemann**, who coined harmonic *function* (Tonic/Dominant/Subdominant) —
  *Harmony Simplified* (Vereinfachte Harmonielehre, 1893). The ancestor of the T/S/D
  table above.
- **Jean-Philippe Rameau, *Treatise on Harmony* (Traité de l'harmonie, 1722).** The
  headwater: chords as rooted entities with roles (the "fundamental bass").
- **Arnold Schoenberg, *Structural Functions of Harmony* (1954).** "Monotonality":
  every chord is understood as a region of *one* governing tonic — the whole-piece
  version of "everything is relative to home."

**The rubber band, as psychology**
- **Leonard B. Meyer, *Emotion and Meaning in Music* (Chicago, 1956).** Meaning and
  feeling arise from the arousal and (de)fulfillment of *expectation*; affect is the
  deviation from the expected. The intellectual root of "music = managed deviation."
- **David Huron, *Sweet Anticipation* (MIT, 2006).** The cognitive-science update —
  why confirmed and violated expectation *feel* the way they do. The empirical
  backbone of the rubber band.

**The rubber band, as a number (closest to a spec)**
- **Fred Lerdahl, *Tonal Pitch Space* (Oxford, 2001),** with **Lerdahl & Jackendoff,
  *A Generative Theory of Tonal Music* (MIT, 1983).** GTTM is itself *generative*
  (apt for a generator); *Tonal Pitch Space* gives tonal tension and distance-from-
  home an actual quantity. If the engine ever models "how stretched the band is,"
  this is where the math comes from.

**Stasis as a literal sonic ground**
- **The tanpura drone in Hindustani classical music** — the most direct real-world
  "A 440 / home": a continuous tonic against which every melodic move is heard as
  departure. The Western cousin is the **pedal point**.
- **Minimalism — La Monte Young, and the project's own Reich & Glass** (see
  [music-theory companion → process](music-theory-companion.md#process-music-reich-glass),
  and `songs/four_organs.yml`): stasis and *perceptible, gradual* deviation as the
  entire content. The `--process` mode is this principle already in the code.

---

## See also

[Music-theory companion](music-theory-companion.md) (full bibliography) ·
[ADR-0006: Interrupters](decisions/0006-interrupters.md) ·
[How harmony works](how-harmony-works.md) ·
[Literal-mode / vamp audit](../design-notes/literal-mode-workflow-audit.md) ·
[Roadmap](../design-notes/roadmap-phase2.md)
