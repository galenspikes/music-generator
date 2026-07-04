# UI/UX roadmap — the webapp instrument

*Forward-looking. Consolidates [gap-analysis.md](gap-analysis.md)'s Phase 0 (reach a
controllable home) and Phase 4 (present it), [webapp-ui-design.md](webapp-ui-design.md),
[large-efforts-tradeoffs.md](large-efforts-tradeoffs.md)'s Phase 4 trade-offs, and the
user's own answers in [ui-homework.md](ui-homework.md) /
[ui-homework-2.md](ui-homework-2.md) into one sequenced plan, plus a new thread (Sound &
Instrument switching) the prior docs flagged but didn't plan. This is the active roadmap
for the React webapp (`webapp/frontend/`) — the primary surface going forward.*

**Scope decisions (locked, 2026-07-04):**
- **Primary surface: the React webapp.** The HF Space and static showcase stay
  promotional/secondary; new UX work lands here.
- **Visual direction: keep the tactile hardware-synth aesthetic** (Bazille visual
  density + tactility, DM-1's sequencer grid and per-pad feel) already underway
  (knob click-to-edit, mobile-first redesign). Not up for reconsideration.
- **Fugue is parked, reaffirmed.** This was already decided in gap-analysis.md's
  2026-06-18 instrument-first call (`mode`/`process`/`fugue` removed from the UI
  surface). Nothing in this roadmap touches fugue development; it comes much later,
  after the core instrument is right.
- **Lead-sheet import is deferred.** [leadsheet-import-plan.md](leadsheet-import-plan.md)
  stays a planning doc only — no work starts until the threads below ship, since the
  point of a lead-sheet importer is to feed a UX that's worth feeding.
- **Engine controllability and UI presentation run in parallel**, not sequentially —
  Thread A (below) and Thread C aren't gated on each other; both are "the core" and
  both need to be perfected together.
- **New thread added: Sound & Instrument switching** — soundfonts and instrument
  choice should be easy and fun, which today it isn't (see Thread D).

---

## Thread A — Reach a controllable, faithful home *(engine-facing; small, do first)*

This is [gap-analysis.md](gap-analysis.md) Phase 0, spec'd in
[controllability-audit.md](controllability-audit.md). It's listed here because it's a
prerequisite for an *honest* control surface — right now several knobs lie (defaults
that can't reach off, controls whose output doesn't match what's set).

- Neutralize the rest-state: percussion off (`--no-perc`, empty `perc_main` = silence),
  no forced interrupter fill, `bass-style: none`, a static/literal voicing option.
- Kill the faithfulness leaks: `satb` block voicing shouldn't reshuffle an unchanging
  chord; literal colon-token chords (`C::maj7`) should never get an engine-chosen
  quality substituted in.
- Cut the baggage already flagged for removal from the surface: `mode`, the
  process/fugue group, and CLI/render plumbing (`out`, `no_play`, `song`, `poly`,
  `perc_lib`) — plus `sf2` specifically, which Thread D replaces with a real picker
  rather than a raw path field.
- **Why first:** it's small, fixes real defects (you currently can't render "just
  this chord, nothing else"), and every other thread below assumes the controls do
  what they say.

---

## Thread B — Presets as the primary UX

Per the homework: *"presets are a must, the more the better,"* and the opening
experience should be *"the home, or a user-defined home preset."* Today's Library tab
(`App.jsx:320-350`) already has song cards + a save-as-preset modal — this thread
finishes what's half-built rather than starting fresh.

**Open questions to settle before building further** (from
[ui-homework-2.md](ui-homework-2.md) §1, left unanswered — worth a short follow-up
round, not blocking Thread A/D):
1. Is a preset always a *full* snapshot of every control, or can it be partial
   (e.g. "just the percussion settings," layered on top of whatever's currently set)?
2. Naming/browsing: typed name vs auto-name, list vs grid, tags/search?
3. Preset vs *song* — is a song a sequence of presets, or a separate concept
   (it already is one, structurally — arrangement YAML)?

**Direction (no reversal needed on what's already decided):**
- The instrument should boot into a **user-selectable home preset**, not always the
  same hardcoded default — the homework explicitly said the current placeholder
  home is provisional until the user crystallizes one by experimenting.
- Session outputs stay plural, per the homework: MIDI, WAV, a saved preset, or a
  saved song — "any of these could be imported into a DAW." No single "the" output.
- Undo/history within a session is explicitly **undecided** (homework: *"we should
  consider options"*) — don't build it yet; flag it as an open question when this
  thread is scoped in detail.

---

## Thread C — Present the control surface as an instrument

This is Phase 4 from gap-analysis.md / large-efforts-tradeoffs.md, updated with the
homework's explicit steer.

**A correction to the older plan:** [webapp-ui-design.md](webapp-ui-design.md)'s
"Simple view + Details toggle" (hide most of the rack by default) is **superseded**.
The homework rejected exactly this: *"i prefer everything but the kitchen sink"* and
refused to rank controls structural→textural (*"i refuse to do this, its against the
spirit"*). The built tab model (Listen / Library / Editor / Docs) already diverged
from the toggle plan — treat that divergence as correct, not a gap to close. Nothing
in the rack should be hidden behind a "details" gate; depth is the point (homework
§4c: *"its meant to be deep"*).

What's actually worth building, per large-efforts-tradeoffs.md's recommendation ("D
grown out of B" — evolve the structured editor, add a small always-on performance
front door) **without hiding anything**:
- **Finish the transport bar** — webapp-ui-design.md's persistent BPM / master volume
  / big PLAY was never fully built (today it's a reroll button + status text,
  `App.jsx:260-267`). Cheap, and matches "instrument, not settings page."
- **Grow the DM-1-flavored sequencer grid.** The homework calls this out by name as
  the thing they love (§4b) — `PercEditor`'s drum grid is the closest existing
  analog. Worth asking: does this grid feel extend to other rhythmic/step controls,
  or stay perc-only?
- **Continue the Bazille-flavored tactility** — knob work (drag, scroll, click-to-edit)
  is solid; keep it as the default control widget, mobile falling back to sliders
  where dragging fights scroll (already the pattern in `controls.jsx`).
- **Piano roll stays, add the waveform display** from the original design doc — still
  missing (`webapp-ui-design.md:90`), cheap, visual feedback the homework's "30-minute
  session" scenario would actually use to see what's happening.

---

## Thread D — Sound & instrument switching *(new)*

The explicit ask: make it easy and fun to change sounds and instruments, including
using soundfonts beyond the one hardcoded today.

**Where it stands today** (confirmed in code):
- The webapp plays MIDI client-side through one hosted General-MIDI soundfont
  (Magenta's `sgm_plus`, `App.jsx:299`) — no soundfont choice exists in the browser
  path at all.
- Instrument selection is a single native `<datalist>` autocomplete
  (`InstrumentPicker`, `App.jsx:469-484`) over ~40 hardcoded `GM_ALIASES`
  (`mtheory.py:67-110`) — no preview-on-click, no categories, typing a raw GM number
  (0–127) works but is undiscoverable.
- A **per-voice** instrument override already exists in the engine
  (`--voice-instrument VOICE=NAME`) but has **zero webapp UI** — direct hit against
  "easy... to change instruments."
- A separate, CLI-only master path (`render.py --sf2`) renders through FluidSynth +
  a single local `.sf2` (`SoundFonts/arachno.sf2` by default). The `sf2` field exists
  in the webapp's schema but is inert for browser playback
  (`music_generator.py:1014-1024` — the code path is commented out) and
  controllability-audit.md already flags it as baggage to cut in its current form.
- [large-efforts-tradeoffs.md](large-efforts-tradeoffs.md) names "preview (Magenta
  soundfont) vs. master (FluidSynth + arachno.sf2)" as an explicitly **undecided**
  question. This thread is where it gets decided.

**Proposed sequencing:**
- **v1 — upgrade what exists, no new infra:**
  1. Replace the bare datalist with a real instrument picker: grouped/categorized,
     click-to-preview (play one note through the current soundfont), still one GM
     program per voice.
  2. Surface the per-voice instrument override in the Editor rack — the engine
     already does this; it's a UI gap, not an engine gap.
- **v2 — a soundfont library/browser (the actual ask):**
  3. Bundle/host a small curated set of soundfonts (a few permissively-licensed
     `.sf2`s beyond the single Magenta default) and add a picker to swap the whole
     palette, not just the GM program within one bank.
  4. Resolve the preview-vs-master question from large-efforts-tradeoffs.md: once
     the webapp can pick a soundfont, decide whether `render.py`'s local master
     render uses that same choice (unifying preview = master) or keeps a documented,
     deliberate split.
- **v3 — stretch, only if v2 lands well:** per-voice soundfont assignment (not just
  per-voice GM program) — e.g. drums from one bank, epiano from another. Bigger
  surface area; revisit after v2 proves out the single-soundfont-swap UX.

---

## Suggested sequencing

Threads A and D-v1 are independent and both cheap — start them together. B and C
depend on some open questions (preset semantics, transport-bar scope) that are worth
a quick decision pass, but don't block starting.

1. **Thread A** (controllable home) — small, fixes real bugs, makes every later
   control honest.
2. **Thread D v1** (instrument picker + per-voice UI) — contained, high delight,
   no dependency on A.
3. **Thread B** (nail preset semantics, finish the Library-as-home-preset flow).
4. **Thread C** (transport bar, sequencer-grid growth, waveform display).
5. **Thread D v2/v3** (soundfont library, preview/master unification, per-voice
   soundfonts) once v1 is proven.
6. **Later, explicitly not now:** lead-sheet import (once this roadmap's threads
   ship), fugue development.

---

## See also

[Gap analysis](gap-analysis.md) · [Controllability audit](controllability-audit.md) ·
[Large-efforts trade-offs](large-efforts-tradeoffs.md) · [Webapp UI design](webapp-ui-design.md)
(superseded in part — see Thread C) · [UI homework](ui-homework.md) /
[UI homework 2](ui-homework-2.md) (source of the user's own answers this roadmap
builds from) · [Roadmap phase 2](roadmap-phase2.md) (engine feature threads, now
secondary to this doc for UI-facing work) · [Lead-sheet import plan](leadsheet-import-plan.md)
(deferred) · [Refactor plan](refactor-plan.md)
