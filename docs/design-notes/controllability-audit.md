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

| Control | Problem | Evidence |
|---|---|---|
| `perc_main` | empty → forced `"sh,sh,sh,sh"`; drums can't be silenced | [mg:2659](https://github.com/galenspikes/music-generator/blob/main/music_generator.py) |
| `perc_interrupters` | empty → forced default fill | [mg:2662](https://github.com/galenspikes/music-generator/blob/main/music_generator.py) |
| `bass_style` | no `none`; bass mandatory | [mg:3165](https://github.com/galenspikes/music-generator/blob/main/music_generator.py) |
| `satb_style` / `voicing` | no *static* option — `block` still voice-leads | [arch:107](../explanation/architecture.md) |

*Partial existing escape:* `voicing: dense` sounds every tone on one channel — close to
a faithful static stack, but it isn't the default and drops voice independence.

## ⚠️ Leaks — output ≠ controls (faithfulness failures)

| Control | Problem |
|---|---|
| `satb` voicing (default) | the chord you set is re-voiced every hit (the wobble) |
| `chords` + `chords_order=random` | bare roots get engine-chosen qualities. Colon tokens (`C::maj7`) bypass this and *are* faithful. |
| `perc_fill_rate=0.2` | fills fire unbidden even when none are wanted |

## ✂️ Baggage — not instrument controls (cut from the surface)

`mode` · the **Process/fugue** group (`process*`, `fugue*`) · CLI/render plumbing
leaking into the UI: `out`, `no_play`, `song`, `sf2`, `poly`, `perc_lib`. Cutting these
follows the [instrument-first decision](gap-analysis.md#decision-instrument-first-2026-06-18).

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
