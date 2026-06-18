# How percussion works

*Explanation — how a percussion token becomes a groove that varies without losing
the pocket. For syntax see [reference/token-grammar.md](../reference/token-grammar.md)
and the [percussion letter map](../reference/percussion-letters.md); for *why*, see
the [ADRs](decisions/).*

## From token to hits

A percussion token is `<duration><letters>[modifiers]`. Parsing
(`parse_single_token`) turns it into one or more **`PercHit`** records, each
carrying:

- a **duration** (`w h q e s t` → beats),
- one or more **instrument letters** played simultaneously (`r` = rest), each
  mapping to a General MIDI drum note,
- and three optional per-hit **modifiers**:

| Modifier | Field | Meaning |
|---|---|---|
| `[vel±N]` | `vel_offset` | shift velocity by N (applied *before* humanization) |
| `[probX]` | `probability` | the hit sounds with probability X (0–1) |
| `[flamX]` | `flam` | add a grace hit X beats later |

So `qb[vel+10,prob0.5,flam0.1]` is a quarter-note kick, +10 louder, that sounds 50%
of the time, with a flam 0.1 beats after. Crucially, `prob` lives on the *note*:
the written pattern describes a **distribution** of performances, not one fixed
take ([ADR-0003](decisions/0003-probability-in-the-token.md)).

## Two tiers of variation

This is the key idea to hold onto: the engine injects controlled non-repetition at
**two different scales**, and they compose.

### Tier 1 — per-hit (micro)
Each `PercHit` with a `probability < 1` is an independent coin flip at render time,
and `vel`/`flam` add human articulation. This is *within-pattern* jitter: the same
bar played twice differs in its ghost notes and accents, the way a human drummer is
never identical twice.

### Tier 2 — per-cycle (phrase): interrupters
At the level of the *whole pattern*, the engine may **substitute** an alternative
([ADR-0006](decisions/0006-interrupters.md)):

```python
def choose_perc_pattern(main, interrupters, fill_rate):
    if interrupters and fill_rate > 0.0 and random.random() < fill_rate:
        return random.choice(interrupters)   # a fill, this cycle
    return main                              # the groove, most cycles
```

Each cycle, with probability `fill_rate` (default 0.20), the main beat is replaced
by a random interrupter — a fill. It's **substitution, not addition**: the
interrupter takes the slot rather than layering on top, so one die-roll per cycle
keeps the groove rhythmically intact. `fill_rate` is the knob with the clearest
musical meaning — ~0.05 is hypnotic and locked, ~0.4 is busy and restless.

The same idea applies to **harmony** via `--chord-interrupters` (rhythmic chord
motifs of "play the chord" / "rest" events), and the **main beat itself** is written
in the same token grammar as the interrupters — there is no separate "main pattern"
syntax.

### Why two tiers
They answer different musical needs and shouldn't be conflated:

| | Scale | Mechanism | Musical effect |
|---|---|---|---|
| Tier 1 | a single hit | `[prob]` / `[vel]` / `[flam]` | human micro-feel, ghost notes |
| Tier 2 | a whole pattern | interrupter `fill_rate` | fills, phrase-level variation |

Together they're how a fixed, looping ostinato avoids sounding like a loop.

## Humanization

Velocity offsets are applied *before* a humanization pass, so `[vel+10]` shifts the
intended accent and the engine still adds its own subtle variation on top, rather
than producing identical velocities every hit. (Swing/feel options exist as coarse,
global controls alongside the per-hit modifiers.)

## What this does and doesn't solve

Both tiers produce **non-repetition** — they keep the groove from being mechanically
identical. They do **not** produce **development**: there's no built-in sense of a
groove *building* or *arcing* over several minutes beyond the (limited) fill-curve
staging. That long-form narrative is the genuine open problem of the ostinato vision
(noted honestly in [ADR-0006](decisions/0006-interrupters.md) and the roadmap).

## Where this sits in the field

Probabilistic hits and pattern substitution are standard in the live-coding lineage
(TidalCycles `?`, `sometimes`, `degrade`) and in drum machines (stochastic fills).
The approach here is an independent re-derivation, not an invention; its distinctive
quality is having both tiers expressed in the *same hand-writable notation* you
compose the groove in.

## See also

- [ADR-0003 — probability in the token](decisions/0003-probability-in-the-token.md)
- [ADR-0006 — interrupters](decisions/0006-interrupters.md)
- [How harmony works](how-harmony-works.md)
