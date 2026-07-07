# How harmony works

*Explanation — how a chord token becomes four voiced, voice-led notes. For the
syntax, see [reference/token-grammar.md](../reference/token-grammar.md); for *why*
the design is shaped this way, see the [ADRs](decisions/index.md).*

## From token to chord

A colon token (`C::maj7`) is parsed into a `ChordDef`: a root pitch class, the set
of pitch classes from applying the [recipe](../reference/chord-recipes.md), and an
optional bass. At this point a chord is just an unordered set of pitch classes —
it has no register, no voicing, no top line. Turning that set into music is the job
of the **voicing engine**.

## SATB voicing: `realize_SATB`

The default voicing realizes each chord as four voices — **S**oprano, **A**lto,
**T**enor, **B**ass — each kept in its own register. The order of operations
matters and encodes the engine's priorities:

1. **Bass first, and fixed.** The bass takes the root (or an explicit slash/inversion
   `bass_pc`) placed low in `BASS_RANGE`. Harmony is anchored from the bottom.
2. **Soprano second, and chosen carefully.** The top line is the one a listener
   actually follows, so it's picked by a dedicated scorer (below) *before* the inner
   voices — the melody-bearing voice gets first claim on the best note.
3. **Tenor and alto fill in.** The remaining chord tones are assigned to the inner
   voices, each pulled into its range, preferring tones that haven't been used yet
   and avoiding collisions (if alto lands on tenor, it's nudged by a step).

### Guide tones vs. color tones

Before voicing, the chord's pitch classes are split into two sets — this is real
functional-harmony thinking, not an arbitrary bucket:

- **Guide tones** — the **thirds** (interval 3 or 4) and **sevenths** (10 or 11).
  These define the chord's quality and function; they're the notes you must hear.
- **Color tones** — the extensions (9ths, 11ths, 13ths, etc.), i.e. everything that
  isn't a guide tone, the root, or the fifth.

The fifth is treated as nearly disposable, and on extended chords (more than three
tones) the **root becomes optional** in the upper voices — because the bass already
states it, and doubling it on top wastes a voice that could carry color. This is why
the engine can voice a `maj13` without sounding cluttered: it prioritizes guide
tones, spends remaining voices on color, and drops the root and fifth when crowded.

## The soprano scorer: `pick_soprano`

The top voice is chosen by minimizing a small weighted cost function over the
candidate chord tones (one per chord pitch class, mapped into `SOP_RANGE`,
C4–G6 — deliberately high so the top voice can "soar and scream"):

| Term | Effect | Why |
|---|---|---|
| **step cost** = `\|note − prev_sop\|` | prefer the nearest note to the previous soprano | smooth voice-leading; small melodic steps |
| **repeat penalty** (+12 if identical to prev) | strongly avoid repeating the exact same note | anti-stagnation — the line must *move* |
| **height penalty** (above ~F6) | gently discourage extreme highs | keep it singable, not shrill |
| **guide-tone bonus** (−3) | prefer landing on a third/seventh | put the chord's *meaning* on top |
| **color bonus** (−1.5) | otherwise prefer a color tone | make the top line interesting |
| **root penalty** (+5 when root is optional) | avoid a root on top of an extended chord | don't waste the lead voice on the least informative tone |

After the minimum is chosen, there's an explicit **anti-stagnation** step: if the
"best" note is the same as the previous soprano, the engine forces a step away
(±1 or ±2 semitones). A static top line is treated as a failure even when it's
locally cheapest.

This single scorer is the source of the project's signature sound, and it traces
directly to the founding design demand (Sept 2025): *"really every note should
change… whatever makes contrapuntal sense, but we want this to be flowing."*

## A worked example

Voicing `C::maj9` (pitch classes C D E G B), the engine splits the tones:

```
all pcs : C D E G B
guide   : E B      (the 3rd and 7th — the chord's identity)
fifth   : G        (disposable)
color   : D         (the 9th — the interesting extension)
root    : C         (stated by the bass; optional up top, since 5 tones > 3)
```

Now voice the progression `C::maj9 → A::min11 → F::maj7 → G::13`, soprano-first,
tracking the actual top line (real engine output):

| token | bass | tenor | alto | soprano |
|---|---|---|---|---|
| `C::maj9`  | C3 | E4 | D4 | **B3** |
| `A::min11` | A2 | G3 | B3 | **C4** |
| `F::maj7`  | F2 | E4 | C4 | **A3** |
| `G::13`    | G2 | F4 | A3 | **B3** |

Read the soprano column: **B3 → C4 → A3 → B3** — every move is a step or less, and
each landing is a guide tone (the 7th of Cmaj9, the 3rd of Amin11, the 3rd of Fmaj7,
the 3rd of G13). That's the `pick_soprano` scorer at work: minimal motion, guide-tone
bonus, no static repeats. The inner voices fill the remaining tones; the bass states
each root. This single column is the project's "flowing" sound made concrete.

## Voicing styles

`realize_SATB` produces **block** chords (all voices strike together). Other
`--voicing` styles reuse the same chord realization but distribute it differently in
time:

- **block** — homophonic; every voice sounds the chord together.
- **arpeggio** (`build_arpeggio_events`) — the voices are spread into arpeggiated
  motion with light timing/pitch jitter for life.
- **counterpoint** (`build_counterpoint_lines`) — voices move as semi-independent
  lines between chord targets, for contrapuntal texture.
- **dense** — sounds *every* chord tone on an ensemble channel (no SATB reduction);
  used when you want the full, thick voicing.

The **bass is decoupled** from all of these (`--bass-style`): it can pulse, leap in
octaves, alternate root/fifth, walk, or arpeggiate independently of the upper-voice
style, while still honoring any slash/inversion bass.

## Where this sits in the theory

The voice-leading approach here — choosing each chord's voicing to **minimize total
motion from the previous chord while preferring functionally important tones** — is
a lightweight, heuristic cousin of the formal voice-leading frameworks: Tymoczko's
geometry of voice-leading (smooth motion as short paths in chord space) and the
classical guide-tone practice of jazz arranging. It is not novel; it is a sound,
taste-driven implementation of well-understood ideas. See the
[music-theory companion](music-theory-companion.md) for the references.

## See also

- [ADR-0002 — named chord recipes](decisions/0002-named-chord-recipes.md)
- [How percussion works](how-percussion-works.md)
- [Architecture — data flow](architecture.md)
