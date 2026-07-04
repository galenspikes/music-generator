# Gap analysis — the engine vs. the instrument it wants to be

*Forward-looking. Measures the current architecture and implementation against the
**intended model** articulated in [Stasis and function](../explanation/stasis-and-function.md):
an always-on instrument with a **home** that you reach by writing nothing and then
*modulate*. Most gaps below are facets of one mismatch — the code is a **batch
generative composer**; the goal is an **always-on instrument**.*

Honest framing first: **measured as a generative composer, the architecture is
sound.** The token DSL is clean, the duration vocabulary is unified, the generative
modes work, and the in-process API (`generator_api.generate`) is fast and well-typed.
The gaps appear only because the project is steering toward an instrument.

---

## The target aesthetic

The instrument's territory: **long-form modal and harmonic exploration** — Neu!, krautrock-adjacent, modal jazz, generative ambient. Music that runs for 20–30 minutes, hypnotic, internally consistent, *too taxing for a human to play* at the required precision and duration. The machine earns its place by sustaining what a player cannot. Sessions produce MIDI, WAV, or saved presets — all routes to a DAW.

## The yardstick (the intended model)

Five invariants, drawn from the design conversations:

- **M1 — the atom.** Every moment is *play or rest, for a quantized duration*
  (`w/h/q/e/s/t`).
- **M2 — the home.** An always-on idle state the instrument boots into — reachable by
  writing *nothing* (the "A 440," the theremin's idle tone).
- **M3 — music = deviation.** Everything expressive is modulation *away from* the home.
- **M4 — always-on.** Press play → it runs; modulate a parameter → you hear the change.
- **M5 — presentation.** The home and the controls ("antennae") are *shown*; you
  manipulate directly, you don't compose flag strings.

---

## What's solid (explicitly not gaps)

- **Unified duration vocabulary** — `DUR_MAP` ([music_generator.py:1181](https://github.com/galenspikes/music-generator/blob/main/music_generator.py))
  is shared by chord length, percussion, and melody. The *duration* half of M1 is done.
- **The token DSL** — literal, composable, well-tested (the crown jewel).
- **Typed, in-process API** — `generate(spec) -> GenerationResult` returns MIDI bytes
  + track info + warnings; no stdout scraping.
- **A real deviation primitive** — interrupters + `fill_rate` ([ADR-0006](../explanation/decisions/0006-interrupters.md)).

---

## Architecture gaps

| # | Gap | Intended → Actual | Evidence | Severity |
|---|---|---|---|---|
| **A1** | **No home is representable** | M2 → there is no "home" concept anywhere; defaults are scattered across argparse + hard-coded fallbacks | no ground-state object; [music_generator.py:2659](https://github.com/galenspikes/music-generator/blob/main/music_generator.py) | **Critical** |
| **A2** | **Batch generator, not a live instrument** | M4 → pure offline render-to-file; the webapp is `POST spec → finished MIDI` | no transport/clock/stream/loop anywhere; [webapp/backend/app.py:111](https://github.com/galenspikes/music-generator/blob/main/webapp/backend/app.py) | **High** (generate-then-play is acceptable; always-running is a future enhancement, not a prerequisite) |
| **A3** | **The atom isn't first-class** | M1 → duration vocab *is* unified, but events are not: three siloed builders merged late as string-tagged tuples; **rest is not an object** | `build_chord_timeline:1746` / `build_drum_timeline_*:1802+` / `_apply_melody`; events `("drum",…)`/`("densechord",…)` | **High** |
| **A4** | **Deviation floats free of a home** | M3 → interrupters exist but anchored to nothing, *generated* not *modulated*, and *stochastic* not *shaped* | `fill_rate` flat probability; ADR-0006's own "non-repetition ≠ development"; no tonal-distance model | **High** |
| **A5** | **No home/deviation structure in the control surface** | M5 → ~40 flat CLI flags / a YAML schema; compose strings, don't manipulate | `build_parser()`; webapp frontend early | **High** (UX/webapp) |
| **A6** | **The lanes are blind to each other** | an ensemble responds to itself → chords, percussion, and melody are realized in *isolation* and merged blind; none can react to another (drums can't accent a chord change, comping can't answer the melody, register can't open as density rises) | separate builders concatenated in `build_flat_midi`; no shared state/clock the lanes read | **High** |

**A1** is the load-bearing one (no home; no neutral). **A2** is real but the playback model is **triggered** (press play → generates → plays → stop → silence), not always-running — generate-then-play is acceptable and matches the current architecture. **A6** —
surfaced only when we drew the [flow model](../explanation/data-flow.md) as a tree —
is the distinct ceiling on how *musical* the output can get: parallel lanes that
never see each other cannot play as an ensemble. It is close kin to **A3** (that one
is about the *representation* — no shared event atom; this one is about the *absence
of shared state during realization*), and both are fixed by giving the lanes a shared
spine to read and write.

---

## Implementation gaps (verified against code)

| # | Gap | Confirmation | Severity |
|---|---|---|---|
| **I1** | **Percussion can't be turned off** | `--perc-main ""` is falsy → forced `"sh,sh,sh,sh"`; no `--no-perc`. *This is the exact reason a one-chord scheme renders with an uninvited beat.* [music_generator.py:2562,2659](https://github.com/galenspikes/music-generator/blob/main/music_generator.py) | **High** |
| **I2** | **Default fill loaded despite "zero interrupters"** | `if not plan_intr: plan_intr = [...]` [:2662](https://github.com/galenspikes/music-generator/blob/main/music_generator.py) | Medium |
| **I3** | **Bass is mandatory** | `BASS_STYLES` has no `none`; default `follow` [:3165](https://github.com/galenspikes/music-generator/blob/main/music_generator.py) | Medium |
| **I4** | **Defaults are non-neutral and scattered** | neutral input yields a full groove; no single source of truth for "the neutral start" | **High** (root cause of A1) |
| **I5** | **Duration is seconds XOR bars** | flat path `--seconds` (default 60, [:3284](https://github.com/galenspikes/music-generator/blob/main/music_generator.py)); song path `bars`/`repeat` ([arrangement.py](https://github.com/galenspikes/music-generator/blob/main/arrangement.py)); they never meet | Medium |
| **I6** | **No static voicing** | `build_harmony_events` always voice-leads ([architecture.md:107](../explanation/architecture.md)); no "freeze this stack" | Medium |

I1–I4 are arguably real defects for *any* user, not just the instrument vision: **you
cannot render chords-only.** See the [literal-mode audit](literal-mode-workflow-audit.md)
for the I5/I6 angle in depth.

---

## The through-line

I1–I4 are the same finding at different altitudes: **the engine has no neutral — it
cannot do nothing.** Every default is already a small piece of music, so the home is
unreachable by subtraction. And A2 means that even once a home exists, you cannot sit
in it and bend it live — you can only re-compile a finished file.

---

## Decision: instrument-first (2026-06-18)

Decided in session: **the product is an always-on instrument; the batch composer/CLI
is not the point — the function and UX are.** Packaging is **C on a B backbone**: one
instrument-first product over a shared engine. Consequences for this plan:

- **The modes collapse into one model.** Fugue, process, and "ostinato-as-a-mode" were
  accretions and are **parked** — pulled off the product surface and the roadmap (keep
  the engine, DSL, and harmony/voicing; remove `mode`/`process`/`fugue` from the UI).
  There are no modes; there is an instrument with a **home** you deviate from.
- **Arrangement is downstream, not a phase to design.** Once the instrument is "a home
  plus control positions," a song is just those positions *automated over time* — the
  most solved pattern in synths. It falls out of the live instrument.
- **Controllability is the near-term whole.** "Reach the home" (Phase 0) is reframed as
  *make the control surface complete + faithful* — see the
  [controllability audit](controllability-audit.md) for the punch-list, and the
  [control-surface companion](../explanation/control-surface-companion.md) for the
  precedent (Kálmán controllability, unity gain, least astonishment).
- **Re-prioritized spine:** Phase 0 (controllable home) + Phase 4 (control surface +
  presets + grid) + Phase 1 (the atom) as substrate. Phase 3 (live transport) is an
  enhancement, not a prerequisite — triggered generate-then-play is acceptable. Phase 2
  (tonal-distance) demotes from a research phase to *one antenna* (likely a macro-knob).
  Mode-pruning is a small cleanup folded into Phase 0.

## Remediation plan (phased)

Sequenced by dependency and by value-per-effort. Status: **all Proposed.**

### Phase 0 — Reach the home *(cheap, high value, fixes real bugs)*
**Closes:** I1, I2, I3, I4 → A1 (partial). **Spec:** [controllability-audit.md](controllability-audit.md).
- Treat an explicit empty `--perc-main ""` as **silence**; add `--no-perc`.
- Respect an explicit empty interrupter list (don't force `"qk,er,qs,er"`).
- Add `bass-style none`.
- Define a single **`GroundState`** config: the one source of truth for "what plays
  when nothing is said," and make it *neutral* (a held chord on the pulse, no forced
  groove). Wire argparse + arrangement defaults to it.
- **Outcome:** the app can render its own idle, and a one-chord scheme comes out
  clean. This also delivers the literal **home/`vamp`** the
  [literal-mode audit](literal-mode-workflow-audit.md) asked for.
- **Effort:** small. **Risk:** low (guard with the smoke tests; defaults change, so
  pin expected output).

### Phase 1 — Unify the atom
**Closes:** A3 (and lays the shared timeline that A6 needs).
- One `Event` type (`kind=play|rest`, `dur`, `payload`); make **rest** explicit.
- The three builders emit into one timeline; `render_events` consumes the unified
  stream. Fold into the [refactor plan](refactor-plan.md).
- **Outcome:** the substrate M4 needs. **Effort:** medium (internal). **Risk:**
  medium — touches every render path; lean on `tests/test_integration.py`.

### Phase 2 — Anchor and shape deviation
**Closes:** A4, A6 — the shared tension/state signal *is* the **shared spine** the
lanes read, which is what lets them finally respond to each other.
- A **tonal-distance / deviation model**: a computed tension that rises as harmony,
  register, and density depart from the home, with a resolution bias (Lerdahl's
  *Tonal Pitch Space* is nearly a spec — see [stasis-and-function](../explanation/stasis-and-function.md)).
- Make `fill_rate` (and harmonic motion) a *shaped trajectory*, not a flat
  probability — solves ADR-0006's "non-repetition ≠ development."
- **Outcome:** "functional harmony in the code," not just the ear. **Effort:** large
  (research-y). **Risk:** medium.
- **Trade-offs & alternatives:** [large-efforts-tradeoffs.md](large-efforts-tradeoffs.md) (Phase 2).

### Phase 3 — Live transport *(enhancement, not prerequisite)*
**Closes:** A2 (fully).
- A running clock that accepts **live parameter modulation** (a param bus + incremental
  scheduling), instead of whole-file re-render. Depends on Phase 1's unified events.
- **Outcome:** adjust a control and hear the change on the next beat without stopping.
  **Effort:** large (new subsystem). **Risk:** high.
- *Note:* the playback model is triggered (generate-then-play), which is acceptable and
  already works. This phase makes it *live*, not *functional* — deprioritized relative
  to Phase 0 + control surface work.
- **Trade-offs & alternatives:** [large-efforts-tradeoffs.md](large-efforts-tradeoffs.md) (Phase 3).

### Phase 4 — Present it *(parallel with 3)*
**Closes:** A5 / M5.
- The webapp instrument UI: present the home already running, expose deviations as
  visible gestural controls. Depends on Phase 3 having something live to expose.
- See [webapp UI design](webapp-ui-design.md). **Effort:** large. **Risk:** medium.
- **Trade-offs & alternatives:** [large-efforts-tradeoffs.md](large-efforts-tradeoffs.md) (Phase 4).

**Recommended start: Phase 0.** It is small, fixes genuine defects, and is the
prerequisite for the whole "home" idea — the app can't be an instrument until it can
first hold still.

---

## See also

[Stasis and function](../explanation/stasis-and-function.md) (the model) ·
[Literal-mode / vamp audit](literal-mode-workflow-audit.md) ·
[Refactor & hardening plan](refactor-plan.md) ·
[Roadmap phase 2](roadmap-phase2.md) ·
[ADR-0006: Interrupters](../explanation/decisions/0006-interrupters.md)
