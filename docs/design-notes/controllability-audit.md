# Controllability audit — the current web-UI control surface

*Forward-looking. Audits the control surface the web UI exposes **today** against the
two properties defined in the [control-surface companion](../explanation/control-surface-companion.md):
**complete** (every dimension reaches its range, including *off*) and **faithful**
(output = the controls, nothing unbidden), with a neutral rest-state that *is* the
home. This is the concrete spec for **Phase 0** of the [gap analysis](gap-analysis.md).*

## How the surface is built

The control panel is **auto-derived from the engine's flags** — `parameter_schema`
([generator_api.py:476](https://github.com/galenspikes/music-generator/blob/main/generator_api.py)) walks the argparse actions, each
annotated with a group + control type in `PARAM_ANNOTATIONS`. Nothing is hidden — but
**exposure is not control.** The surface fails controllability three ways at once: its
rest-state is maximally deviated, several dimensions have no "off," and a few controls
*generate* rather than *obey*.

## The rest-state is the wrong starting point

Verified engine defaults (`build_parser().parse_args([])`):

| Param | Default | Consequence |
|---|---|---|
| `mode` | `mixed` (CLI) — **UI overrides to `ostinato`** ([App.jsx:29](https://github.com/galenspikes/music-generator/blob/main/webapp/frontend/src/App.jsx)) | UI obeys `keys` ✓ |
| `chord_len` | `e` | eighth-note pulse ✓ |
| `perc_main` | `None` → forced `"sh,sh,sh,sh"` | hi-hat groove, unbidden |
| `perc_interrupters` | `None` → forced `"qk,er,qs,er"` | fill vocabulary, unbidden |
| `perc_fill_rate` | `0.2` | fills fire ~1 in 5 cycles |
| `bass_style` | `follow` | bass on, no off |
| `satb_style` / `voicing` | `block` / `satb` | chord re-voiced every hit |
| `chords` / `chords_order` | `['triads']` / `random` | qualities chosen for you |

The instrument boots maximally *deviated*, not at home.

## ❌ Holes — no neutral/off (completeness failures)

**Status: shipped (2026-07-04)**, per [ui-ux-roadmap.md](ui-ux-roadmap.md) Thread A.

| Control | Problem | Fix shipped |
|---|---|---|
| `perc_main` | empty → forced `"sh,sh,sh,sh"`; drums can't be silenced | explicit `--perc-main ""` (or `--no-perc`) now means silence; unspecified still falls back to the default groove. `percussion.py::build_perc_from_args`, and (a follow-up fix, same pass) the `--song`/arrangement override builders in `music_generator.py` and `generator_api.py`, which had the identical truthy-check bug on their own copy of the logic and never honored `--no-perc` at all. |
| `perc_interrupters` | empty → forced default fill | an explicitly empty `--perc-interrupters` (bare flag, zero values) is now honored as "no interrupters" instead of forcing the default fill vocabulary. Same function. |
| `bass_style` | no `none`; bass mandatory | added `"none"` to `BASS_STYLES`; `build_harmony_events` drops the SATB bass voice entirely and skips `build_bass_line`. |
| `satb_style` / `voicing` | no *static* option — `block` still voice-leads | added `--satb-style static`; `build_chord_timeline(..., static=True)` freezes the exact voicing across an unchanged chord instead of calling `pick_soprano`'s anti-stagnation logic. |

*Partial existing escape:* `voicing: dense` sounds every tone on one channel — close to
a faithful static stack, but it isn't the default and drops voice independence.

## ⚠️ Leaks — output ≠ controls (faithfulness failures)

| Control | Problem | Status |
|---|---|---|
| `satb` voicing (default) | the chord you set is re-voiced every hit (the wobble) | **Fixed for `--satb-style static`** (above); `block` still wobbles by design (voice-leading is the point of `block`). |
| `chords` + `chords_order=random` | bare roots get engine-chosen qualities. Colon tokens (`C::maj7`) bypass this and *are* faithful. | Open — literal tokens already faithful; family-based selection is unchanged. |
| `perc_fill_rate=0.2` | fills fire unbidden even when none are wanted | Open — the *default* fill rate is unchanged; only the "explicit empty means off" bug (above) shipped. Lowering the default is a separate, more opinionated call (see GroundState note below). |

## ✂️ Baggage — not instrument controls (cut from the surface)

**Status: shipped (2026-07-04).** `mode`, the **Process/fugue** group (`process*`,
`fugue*`), and CLI/render plumbing (`out`, `no_play`, `song`, `sf2`, `poly`,
`perc_lib`) are now excluded from `generator_api.parameter_schema()` via
`HIDDEN_PARAMS` — they no longer render as webapp controls, but remain fully
functional on the CLI and in song YAML. Cutting these follows the
[instrument-first decision](gap-analysis.md#decision-instrument-first-2026-06-18).

**Not done in this pass:** the single-source-of-truth `GroundState` config (I4) —
i.e. actually flipping the *default* rest-state to neutral (no groove, no fill,
unless asked) rather than just making neutral *reachable*. Per the user's own
[ui-homework.md](ui-homework.md), the exact home content is still a placeholder
they intend to tune by ear before it's locked in as a default — so this pass
fixes the mechanism (every "off" is now reachable) without changing what
existing renders produce when nothing is specified.

## ✅ Already controllable — keep

`bpm`, `seconds`, `seed`, `chord_len` (the pulse — faithful), `instrument`,
`chord_fill_rate` (off by default), `chord_interrupters` (empty default), `melody` +
subs (off), `perc_stages` (off), `perc_fill_rate` (controllable; just a wrong default),
`velocity_mode_*` (**`uniform` = the neutral/identity — exactly right**).

## Punch-list (Phase 0)

1. **Neutralize the rest-state** so boot = idle: perc off, `fill_rate=0`, static
   voicing, literal chords (no random family pick).
2. **Open the holes:** empty `perc_main` = silence (+ an explicit *Off*); honor empty
   interrupters; add `bass_style: none`; add a static/literal voicing.
3. **Kill the leaks:** static voicing as the instrument default; obey literal chords;
   no unbidden fills.
4. **Cut the baggage** from the surface (mode, process/fugue, render plumbing).

## Acceptance test — the definition of "controllable"

Set `keys = C::maj7`, everything else neutral → hear *exactly* straight Cmaj7 at the
pulse on the chosen instrument, **nothing else**. And: every deviation control at zero
*is* the home.

*Taste call:* the original one-chord scheme kept `bass: follow`, so a root-bass may
belong to the home rather than count as deviation — add `none` for completeness, don't
necessarily strip bass from the idle.

## See also

[Control-surface companion](../explanation/control-surface-companion.md) ·
[Gap analysis](gap-analysis.md) · [Stasis and function](../explanation/stasis-and-function.md)
