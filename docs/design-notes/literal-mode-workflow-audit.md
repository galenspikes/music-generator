# Workflow audit — the "just play this chord" gap

**Triggering question (2026-06-18):** *Can I make a 30-second file, 120 bpm, that is
just straight 1/8th-note block chords of Cmaj7 on an electric piano — no changes?*

The musically trivial answer should be a one-liner. It is not. This note audits
**why**, traces the request through every input path, and lays out options. It is a
*findings* document, not a plan that has shipped.

---

## TL;DR verdict

The request is **achievable today, but only by hand-writing a song YAML**, and even
then it is **not exactly** what was asked:

- ✅ 30.0 s, 120 bpm, straight eighths, Cmaj7 pitch content — all reachable.
- ⚠️ "Block, no changing" is **not honoured** — the SATB voicer reshuffles voices
  between identical chords (upper voice wobbles E↔B every eighth).
- ⚠️ "Just an electric piano" is **impossible in song mode** — you always get four
  SATB voice tracks **plus** an unbidden moving bass, and the single-timbre
  ("dense") voicing is CLI-only.
- ❌ The **obvious** entry point — `--mode ostinato` — **cannot do it at all**.

Root cause: the engine is a **generative composer**. "Play exactly this, repeated,
unchanged" is a *literal* request the tool has no first-class word for.

---

## The request, traced through each path

### Path A — the obvious CLI (`--mode ostinato`): can't do it

The natural first attempt:

```
--mode ostinato --keys C --chords sevenths --chord-length e \
  --satb-style block --bpm 120 --seconds 30 --instrument epiano
```

What you get is **not** a held Cmaj7. `build_flat_midi`
([music_generator.py:2960](../../music_generator.py)) calls `build_progression`
([:1674](../../music_generator.py)) over the chosen chord *family*, producing a
*sequence of different seventh chords* across roots, with shifting voice-leading.
Observed first hits: Bb, G, B, E… — a generated progression, not one chord.

`--keys` is a list of **keys**, not chords; `--chords` is a list of **families**, not
a specific quality. There is no flag anywhere on the flat path that says "this exact
chord, and only this chord." So the most discoverable mode is a dead end for the
literal case.

### Path B — song YAML: gets close

The `keys:` field of a section accepts **explicit chord tokens** in colon notation,
and `maj7` is a real recipe ([library/chord_recipes.py:24](../../library/chord_recipes.py)).
So `C::maj7` pins a literal Cmaj7. Combined with the **`bars:`** length control
([arrangement.py `_section_beats`](../../arrangement.py)), a *single* token tiles to
fill the section:

```yaml
title: Cmaj7 vamp
tempo: 120
defaults:
  instrument: epiano
  satb: block
  chord_length: e
  bass: { style: follow }
sections:
  - name: vamp
    bars: 15          # 15 bars × 4 beats = 60 beats = 30.0 s at 120 bpm
    keys: "C::maj7"
```

Verified output: **exactly 30.0 s, 120 eighth notes per voice, pitch classes
{0,4,7,11} = C-E-G-B.** So the headline ask is met. The gaps are in the details
below.

---

## The three real gaps

### 1. Duration is in **bars**, not **seconds** — and only on one path

- The flat path has `--seconds` but **can't pin a chord** (Path A).
- The song path **can pin a chord** but has **no seconds** — you specify `bars:`,
  and must do the mental math `bars = seconds × bpm / 60 / 4` (here 30 → 15).

The capability the user wants ("a fixed chord, for N seconds") exists only as the
*intersection* of two paths, and neither path spans it. There is no
"repeat/vamp this chord for a duration" primitive on either side.

### 2. "Block, no changing" isn't static

Even with `satb: block`, the SATB voicer redistributes the four chord tones across
the four voices between *identical* chords — so the top voice alternates E↔B every
eighth. The **pitch set** is fixed; the **voicing** is not. There is no mode that
means "sound this exact stack, identically, on every hit."

### 3. "Just an electric piano" can't be expressed in song mode

- Song mode has **no `voicing` key** — `arrangement.py` always uses the four-voice
  SATB path. The single-timbre "sound every chord tone on one channel" mode
  (`--voicing dense`) is **CLI-only** and unreachable from a song file.
- **Bass is mandatory.** `BASE_DEFAULTS["bass"] = {"style": "follow"}`
  ([arrangement.py:30](../../arrangement.py)) and there is no `style: none`, so a
  moving bass voice is always added. The verified output had a bass line (pcs
  {0,2}) nobody asked for.

So "an epiano playing block chords and nothing else" is not a state the song schema
can represent: you get 4 SATB voices + bass, minimum.

---

## Root cause: generative vs. literal

Every path is built around *generation* — pick a family, build a progression,
voice-lead it, add a bass, lay a groove. That is the project's strength. But it
means the **degenerate case** — "no generation, just hold this" — falls through:

| Want | Tool's reflex |
|---|---|
| one fixed chord | build a progression from a family |
| identical every hit | voice-lead between hits |
| epiano only | add SATB voices + bass + (optionally) percussion |
| N seconds | N bars (song) or N seconds-of-progression (flat) |

The user's mental model is **"an instrument I tell what to play."** The tool's model
is **"a composer I give constraints to."** This is exactly the tension the
[webapp UI direction](webapp-ui-design.md) and the
[[webapp-ui-ux-direction]] memory anticipate.

---

## Options (not yet decided)

Ordered by how directly each closes the gap, with trade-offs.

### Option 1 — a literal "vamp" primitive *(closest fit)*
Add a first-class way to say *"hold/repeat this exact chord as straight
subdivisions, for a duration, as a static block."* Sketch:

```
--mode vamp --chord C:maj7 --subdiv e --seconds 30 --instrument epiano --static
```

- Pins one literal chord (reuse the colon-token parser — the crown-jewel DSL).
- `--seconds` already exists; map subdivisions onto it directly (no progression,
  no `build_progression`).
- `--static` (or a "block-literal" voicing) emits the **same stack** every hit —
  no voice reshuffle, no bass unless asked.
- **Pro:** makes the trivial case trivial; composable with existing audio render.
- **Con:** a new mode + a static-voicing code path; must not disturb the token
  tests or the generative paths.

### Option 2 — extend the song schema to be literal-capable
Teach `arrangement.py` to (a) accept `voicing: dense`, (b) accept `bass: none`,
(c) offer a "static/literal" satb style, and (d) accept `seconds:` as an alias for
`bars:`.

- **Pro:** no new mode; song YAML becomes able to express "epiano only, static."
- **Con:** still YAML-authoring for a one-liner; four small schema changes; the
  bars↔seconds duality lingers.

### Option 3 — fix discoverability only (cheapest)
Leave the engine; add a **how-to recipe** ("hold one chord for N seconds") and a
ready-made `songs/vamp.yml`, and document the `bars = s×bpm/240` conversion.

- **Pro:** an hour of work; unblocks the user today.
- **Con:** doesn't fix the wobble, the forced bass, or the multi-track-vs-epiano
  mismatch. Papers over the model gap.

### Option 4 — make it the webapp's job
Treat "play this chord, this rhythm, this long" as the **UI's** responsibility; the
instrument front-end emits the right engine call. Defer any CLI/engine change.

- **Pro:** aligns with the stated product direction; the UI is where "literal" lives
  naturally.
- **Con:** doesn't help CLI/headless users; largest scope; the engine still lacks a
  clean literal call for the UI to make (so likely needs Option 1 underneath
  anyway).

---

## Recommendation

**Option 1 (a literal `vamp` primitive), with Option 3's docs as the immediate
unblock.** Option 1 gives the engine the missing verb — which the webapp (Option 4)
would then call — without weakening the generative core. Options 2 and 4 are better
*after* the engine can express "literal" at all.

*No code has been written for any option. This note records the audit and the
decision space.*
