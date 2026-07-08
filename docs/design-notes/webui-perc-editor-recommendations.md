# Web UI & percussion editor — recommendation plan

*Forward-looking. An external review pass (2026-07-08) over the webapp instrument
(`webapp/frontend/`) with a focus on the percussion editor (`PercEditor.jsx`).
Extends [ui-ux-roadmap.md](ui-ux-roadmap.md) — in particular it proposes an answer
to the sequencer-grid question Thread C deliberately left open — and respects that
roadmap's locked decisions: nothing gets hidden behind a "details" gate, the
tactile Bazille/DM-1 aesthetic stays, and the tab model stands. Tiered by
value ÷ risk, like [refactor-plan.md](refactor-plan.md).*

**A correction first.** An earlier draft of this review claimed the webapp had no
MIDI export. Wrong — `⌘S` and the `⤓ MIDI` link (`App.jsx:689`) already download
the current render. No action needed there.

---

## Findings — percussion editor (grounded in `PercEditor.jsx`)

The editor is already strong: code/grid dual mode, a live drum-letter legend
driven by the served drum map, debounced server-side parse validation with a
per-token chip strip, and groove presets. The gaps below are the places where
the grid mode is *lossy* or where the DSL's expressive features are unreachable
without typing tokens.

1. **The grid covers 8 of the 25 drum letters** (`SEQ_ROWS` is a fixed list:
   kick/snare/hat/open-hat/clap/ride/tom/cowbell). A pattern using any other
   letter gets the "⚠ pattern not a clean grid" warning, and *any* grid edit
   then rewrites the pattern from only the 8 known rows — silently deleting the
   other hits (`valueFromGrid` emits row letters only).
2. **Grid edits destroy per-hit modifiers.** `[vel±N]`, `[probX]`, `[flamX]` are
   stripped on read (`stripMods`) and never re-emitted, so toggling one cell
   deletes every modifier in the pattern. The modifier language — the expressive
   heart of the percussion DSL — is reachable only from code mode.
3. **The chip strip hides modifiers too.** Chips show duration + hit names but
   not vel/prob/flam, so a humanized pattern and a flat one look identical.
4. **No audition below "regenerate everything."** You can't hear one drum row,
   one motif, or one interrupter in isolation. (The instrument picker already
   solved this shape of problem: its ▶ preview plays a minimal vamp through a
   hidden second `<midi-player>` — that mechanism is reusable.)
5. **No playhead.** Nothing highlights the current grid column (or waveform
   position) during playback.
6. **Mobile crowding.** 32 steps × 8 rows of small square buttons with no sticky
   row labels; the grid is the least usable control on a phone.

---

## Plan

### Tier 1 — Make the grid lossless (small; fixes real defects)

- **1.1 Never delete hits: auto-add rows.** When `gridFromValue` meets a letter
  outside `SEQ_ROWS`, add a row for it (the live drum map already supplies the
  label) instead of setting `fits = false` and normalizing it away on the next
  edit. The 8 defaults stay as the empty-pattern starting set; the warning
  banner then only fires for genuinely non-grid patterns (mixed durations).
- **1.2 Never delete modifiers: carry brackets through.** Parse each step's
  bracket text once, keep it attached to (step, letter), and re-emit it verbatim
  in `valueFromGrid`. Toggling cell (kick, 5) must not touch `c[vel-20]` at
  step 3.
- **1.3 Show modifiers on chips.** Small badges on the parse chips
  (`+10`, `50%`, `flam`) so humanized patterns are visibly different.
- **1.4 Row audition.** Click a row's name to hear that drum once — a one-hit
  token through the existing hidden-player preview path.

### Tier 2 — Grow the DM-1 feel (the Thread C open question, answered for percussion)

Thread C left "grow the sequencer grid" open as a taste call. Recommendation:
grow it *inside* the percussion editor only — per-pad expressiveness, not more
grids elsewhere.

- **2.1 Accent / ghost cells.** Repeated taps cycle a cell off → on → accent →
  ghost, emitting `[vel+15]` / `[vel-20]` (exact offsets to taste), rendered as
  cell intensity. This is the DM-1 per-pad feel, and it makes the modifier DSL
  reachable without typing. Depends on 1.2 (round-trip safety) landing first.
- **2.2 Motif audition.** A ▶ on each motif (main and each interrupter) that
  plays just that pattern, looped twice, drums only — same reuse of the preview
  mechanism as 1.4. Interrupters especially are inaudible today until fill-rate
  happens to fire one.
- **2.3 Step playhead.** Highlight the current column during playback.
  Constraint to check first: `html-midi-player`'s position events may be too
  coarse; if so, this lands with the synthesis upgrade (see the synthesis
  recommendation below) rather than being hacked around.
- **2.4 A "+ row" picker** over the full live drum map, grouped
  kicks/snares/hats/cymbals/toms/hand-percussion, for building beyond the
  defaults deliberately (1.1 covers the *reading* side; this is the writing side).

### Tier 3 — Bigger / taste

- **3.1 Do not build a mixed-duration grid.** Per-step durations are genuinely
  at odds with a step grid; the honest tool is a *resolution swap* action
  ("densify" 8×`e` → 16×`s` with rests interleaved, and the reverse where
  lossless) so patterns can move between feels without hand-retokenizing.
- **3.2 Fill visibility.** The waveform strip (Thread C) could mark which cycles
  an interrupter fired in, making `fill_rate` audible *and* visible.
- **3.3 Mobile grid pass.** Sticky row-name column, horizontal scroll on the
  cells only, larger touch targets, default to 8 steps under ~480px (user can
  still select 32 — nothing hidden, just a smarter default).

### Web UI (beyond percussion)

- **Undo/redo, smallest honest version.** The homework left this open
  ("we should consider options"). Proposal consistent with the full-snapshot
  preset ethos: a session-local ring buffer of full spec snapshots (capped,
  ~50), `⌘Z`/`⌘⇧Z`, no persistence, no diffing. It's the preset mechanism
  minus the disk.
- **Per-voice mute/solo.** Stems are already split in `MidiOut`; the browser
  player can't mute channels, so v1 is "regenerate without this voice" behind
  an M/S toggle per voice in the Voicing panel. Slower than a mixer but honest,
  and it makes voice-leading choices — the point of the tool — individually
  audible.
- **Waveform playhead** — same event source as 2.3; ship them together.

---

## Suggested sequencing

Tier 1 is one small PR-sized pass and removes the two data-loss defects (1.1,
1.2) — do it first and alone. 2.1 follows immediately (it depends on 1.2).
2.2/1.4 share the preview-reuse work. 2.3 and the waveform playhead should wait
for the browser-synthesis decision rather than fight `html-midi-player`.
Tier 3 and undo/redo are independent and can ride along with any later pass.

## See also

[UI/UX roadmap](ui-ux-roadmap.md) (Threads C/D — locked decisions this plan
inherits) · [Controllability audit](controllability-audit.md) (the faithfulness
standard: controls must not lie, edits must not lose data) ·
[UI homework](ui-homework.md) / [UI homework 2](ui-homework-2.md) (the taste
constraints: depth, nothing hidden) · [Refactor plan](refactor-plan.md) (the
tiering format).
