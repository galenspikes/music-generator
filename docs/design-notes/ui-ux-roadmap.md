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
- **Lead-sheet import — v1 shipped (2026-07-04).** Was deferred until Threads
  A/B/C/D shipped; they have, so the deterministic core (chord-symbol mapper +
  IR→song.yml emitter) and the extraction workflow are now real — see
  [leadsheet-import-plan.md](leadsheet-import-plan.md).
- **Engine controllability and UI presentation run in parallel**, not sequentially —
  Thread A (below) and Thread C aren't gated on each other; both are "the core" and
  both need to be perfected together.
- **New thread added: Sound & Instrument switching** — soundfonts and instrument
  choice should be easy and fun, which today it isn't (see Thread D).

---

## Thread A — Reach a controllable, faithful home *(engine-facing; small, do first)*

**Status: mostly shipped (2026-07-04).** Percussion and bass can now genuinely be
turned off, chords can be voiced statically (no wobble), and baggage is cut from the
webapp schema. Still open: the single-source-of-truth `GroundState` (flipping the
*default* rest-state to neutral) and the literal `vamp` one-liner — both deferred
until the home's actual content is settled by ear (see [ui-homework.md](ui-homework.md)).
Details in [controllability-audit.md](controllability-audit.md) and
[gap-analysis.md](gap-analysis.md) Phase 0.

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

**Status: v1 shipped (2026-07-04).** Per the homework: *"presets are a must, the
more the better,"* and the opening experience should be *"the home, or a
user-defined home preset."* Today's Library tab already had song cards + a
save-as-preset modal — this pass finished what was half-built, fixed a real
security bug found along the way, and answered its own open questions by
building the smallest thing that resolves them rather than asking.

**A real bug found and fixed first:** `generator_api.py`'s preset (and song)
load/save built the file path directly from an unsanitized name
(`PRESETS_DIR / f"{name}.json"`), reachable straight from an HTTP path
parameter. `pathlib`'s `/` operator doesn't resolve or reject `..` segments, so
`POST /api/presets/../../../etc/passwd` would write outside the presets
directory — a path-traversal vulnerability. Fixed with a `slugify()` that every
preset/song name now passes through on both read and write (kept underscore-
preserving so existing `songs/*.yml` filenames like `four_organs` still
round-trip), plus a resolved-path defense-in-depth check. Covered by tests that
prove the write path can't escape, not just that a bogus read 404s (a
nonexistent traversed path would 404 either way, which doesn't prove anything).

**The open questions, resolved by building, not by asking:**
1. *Full vs. partial snapshot* — stayed **full**: every save captures the
   entire current spec. Matches the project's determinism/reproducibility ethos
   already established elsewhere, and there was no signal favoring partial.
2. *Naming/browsing* — a typed **title** (free text) auto-generates a
   sanitized **slug** for the filename (shown live in the save dialog: "saves
   as: my-cool-groove"), so the two concerns (what you call it / what's safe on
   disk) aren't conflated the way they used to be (same string, no
   sanitization). Browsing stayed the existing grid-of-cards (matches the
   DM-1/Bazille visual density already in place) with a search/filter box added
   over title+description — "the more the better" for presets means this was
   going to get unwieldy fast.
3. *Preset vs. song* — left as-is: two separate concepts (a preset is a full
   parameter snapshot; a song is the existing arrangement YAML). No unification
   attempted; wasn't asked for.

**The home-preset mechanism:** a reserved preset name (`"home"`,
`generator_api.HOME_PRESET_NAME`) is what the app tries to load on boot,
falling back to today's Kiss demo if none is saved. Any preset card gets a
"⌂ set as home" action that promotes it; the save dialog also has a direct
"also use as my home preset" checkbox. The card that *is* home is marked with
a badge so it's never ambiguous which one loads on startup.

**Also added, since it was an obvious gap once delete mattered:** preset
deletion (API + a hover-revealed trash icon per card) — there was no way to
remove a saved preset at all before this.

**Still deliberately not built:** undo/history within a session — the homework
left this explicitly undecided (*"we should consider options"*), so it's left
alone rather than guessed at. Session outputs stay plural as already noted in
the homework (MIDI, WAV, preset, song) — nothing in this pass changed that.

Verified in a real browser session (Playwright): save → appears in Library with
the correct sanitized slug; search filters correctly; set-as-home badges the
right card and survives a reload; delete removes exactly the targeted preset.
Full suite (300+ tests) and repo-wide ruff pass.

---

## Thread C — Present the control surface as an instrument

**Status: v1 shipped (2026-07-04).** Transport BPM and the waveform display are
done; the sequencer-grid question below is intentionally left open rather than
guessed at (a real product-taste call, not an engineering one). See below for
what shipped and a dead-code cluster found and removed first.

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

**A dead-code cluster found and removed before touching the UI.** `--gain`,
`--reverb`, `--chorus`, `--poly` (and `music_generator.py`'s own `--sf2`) were
100% vestigial — referenced only inside a commented-out, unreachable
FluidSynth-launch block from before `render.py` existed as its own wrapper
(the comment even said so: *"playback is now handled by the wrapper
script"*). `gain`/`reverb`/`chorus` were still visible, turnable knobs in the
webapp's Render panel — three controls a user could adjust that changed
nothing, which is a worse faithfulness violation than anything
controllability-audit.md catalogued (those were about wrong *defaults*, not
knobs wired to nothing at all). `poly` was already hidden from the UI in
Thread A but the flag itself was still dead weight. Removed all four flags,
the dead comment block, and their schema entries; `--sf2` on
`music_generator.py` itself turned out to be equally dead (never read outside
that same block) but was left alone since `render.py`'s own independent
`--sf2` is real and the `soundfont:` song-YAML field is genuine, intentional
metadata (present in every `songs/*.yml`) that a future feature could still
read.

- **Finish the transport bar — done.** Added a persistent BPM stepper next to
  Thread D's sound-bank picker (`App.jsx`'s `.transport`). "Master volume" and
  "big PLAY" from the original plan turned out to already exist: the native
  `<midi-player>` element renders its own play/pause/seek/time-display UI
  (confirmed by the existing `::part(time)`/`--pl-*` CSS already styling it) —
  building a second one would have duplicated it, not "finished" it. Couldn't
  fully re-inspect that native UI live in this sandbox (the CDN script serving
  `html-midi-player` is blocked by this environment's network policy), so this
  is based on the CSS evidence already in the codebase, not a fresh screenshot.
- **Waveform display — done.** Added a genuine one rather than a decorative
  placeholder: `generator_api.envelope_from_bytes()` computes a coarse,
  time-bucketed note-density envelope via `mido`'s tempo-aware absolute timing
  (not a hand-rolled JS MIDI parser — tick/tempo math is easy to get subtly
  wrong, and this project already trusts `mido` elsewhere), returned from
  `/api/generate` and rendered as a thin-bar strip above the piano roll.
  Verified in a real browser session: 60 bars render, and changing BPM in the
  new transport control triggers a regeneration that updates the waveform.
- **Grow the DM-1-flavored sequencer grid** — **left open, not built.** This is
  a real product-taste question (does the step-grid feel extend beyond
  percussion to other rhythmic controls, e.g. chord interrupters or the
  melody rhythm cells?), not something to guess an answer to and build around.
  Revisit when there's a specific rhythmic control in mind for it.
- **Bazille-flavored tactility** — unchanged; the existing knob/slider work in
  `controls.jsx` already covers this well, nothing was missing here.

---

## Thread D — Sound & instrument switching *(new)*

**Status: v1 and v2 shipped (2026-07-04).** v3 (per-voice soundfonts) is the
only piece still open. See below for what each version turned out to mean once
the real technical constraints were checked instead of assumed.

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

**v1 — shipped (2026-07-04).** Before touching the picker UI, the underlying
data was too thin to browse: `GM_ALIASES` (`mtheory.py`) was a flat ~40-entry
curated list with only comment-based grouping — no family metadata a picker
could group by, and no path to the other ~90 General MIDI instruments at all.
Fixed the data first: added `GM_CATALOG`, the full 128-program GM Level 1 set
with real `family` metadata (the 16 standard GM families), additive alongside
the existing short aliases (`GM_ALIASES` untouched — still the CLI/song
vocabulary); extended `resolve_instrument` to also resolve full catalog names.
Exposed it via `/api/vocab`'s new `instrument_catalog` field. Only then built
the UI: `InstrumentPicker` gained a "browse" panel — family-grouped, filterable,
click-to-select, click-to-preview (▶) — layered over the existing text+datalist
field (short aliases and raw GM numbers still work unchanged). Preview plays a
literal, undecorated Cmaj7 vamp through the chosen instrument via a hidden
second `<midi-player>`, reusing Thread A's `--no-perc`/`bass-style
none`/`satb-style static` rather than adding a second synthesis path. The
previously-invisible `--voice-instrument` engine feature is now a real per-voice
(soprano/alto/tenor/bass) picker in the Voicing panel, replacing the generic
"type VOICE=NAME" taglist. Verified in a real browser session (Playwright):
16 families / 128 instruments render, filtering narrows correctly, click-select
and click-preview both work end to end against `/api/generate`.

- **v2 — shipped (2026-07-04), scope narrowed by a real constraint.** "Bundle a
  curated set of soundfonts" turned out not to be possible the way originally
  imagined: `.sf2` files aren't usable by the browser at all — `html-midi-player`
  needs soundfonts pre-converted into its own sample-directory format, and only
  two such directories are publicly hosted anywhere (verified, not guessed):
  `sgm_plus` (full GM, the existing default) and `salamander` (piano-only).
  Shipped what's actually real: a **sound-bank picker** in the transport bar
  (General MIDI / Salamander Piano / custom URL for anyone hosting their own
  converted directory), with a warning badge on Salamander since only piano
  will sound correct through it. Persisted in `localStorage`, not saved into
  presets/songs (it's a playback setting, not musical content). Separately, gave
  the **master/CLI side** real soundfont switching, which *is* fully general
  since FluidSynth loads any `.sf2`: `render.py` gained `--list-soundfonts` and
  bare-name resolution against `SoundFonts/` (`--sf2 arachno` instead of a full
  path). The preview-vs-master question from large-efforts-tradeoffs.md is now
  **decided**: a deliberate, permanent split, not a unification — see that doc's
  fact #4 for why unifying would require a real audio-conversion subsystem.
- **v3 — stretch, still open:** per-voice soundfont assignment (not just
  per-voice GM program) — e.g. drums from one bank, epiano from another. Bigger
  surface area, and constrained by the same 2-bank reality above; low priority.

---

## Suggested sequencing

Threads A and D-v1 are independent and both cheap — start them together. B and C
depend on some open questions (preset semantics, transport-bar scope) that are worth
a quick decision pass, but don't block starting.

1. ✅ **Thread A** (controllable home) — shipped.
2. ✅ **Thread D v1** (instrument picker + per-voice UI) — shipped.
3. ✅ **Thread B** (presets, home-preset flow) — shipped.
4. ✅ **Thread C** (transport bar, waveform display) — v1 shipped; sequencer-grid
   growth left open (taste call).
5. ✅ **Thread D v2** (soundfont picker, preview/master decided) — shipped.
   **Thread D v3** (per-voice soundfonts) — still open, low priority, stretch.
6. ✅ **Lead-sheet import v1** — shipped now that the threads above have.
   **Still explicitly not now:** fugue development.

---

## See also

[Gap analysis](gap-analysis.md) · [Controllability audit](controllability-audit.md) ·
[Large-efforts trade-offs](large-efforts-tradeoffs.md) · [Webapp UI design](webapp-ui-design.md)
(superseded in part — see Thread C) · [UI homework](ui-homework.md) /
[UI homework 2](ui-homework-2.md) (source of the user's own answers this roadmap
builds from) · [Roadmap phase 2](roadmap-phase2.md) (engine feature threads, now
secondary to this doc for UI-facing work) · [Lead-sheet import plan](leadsheet-import-plan.md)
(deferred) · [Refactor plan](refactor-plan.md)
