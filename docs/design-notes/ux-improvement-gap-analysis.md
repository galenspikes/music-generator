# UX Improvement Plan — gap analysis

*Assessment of the external "Instrument UX Improvement Plan" against the code as it
actually stands (2026-07). The plan predates the current Library tab, schema-driven
tooltips, and the status/lamp system, so a large share of its items are already done
or only need a content pass. This note records that mapping so the work can be
re-prioritized instead of built blind.*

**Bottom line:** of ~18 plan items, roughly **7 are effectively done**, **6 are
partial**, and **5 are genuinely missing**. Legend: ✅ done · 🟡 partial · ❌ missing.

## Phase 1 — Empty-state onboarding

- **1.1 Welcome overlay** — ❌ **Missing.** No `hasSeenWelcome` flag / overlay; the
  only modal is the Save-preset dialog (`App.jsx`). *But* the app already auto-loads a
  demo on boot (`loadSong("kiss")`) or the user's saved "home" preset, so a first
  visit is already audible. An overlay is additive, not a fix for silence — low
  urgency.
- **1.2 Demo preset selector** — 🟡 **Partial.** A full **Library tab** already exists
  with demo songs *and* saved presets, a filter box, and active-state. Backend already
  serves `/api/songs` + `/api/presets`, so the proposed `/api/presets/list` is
  redundant. Missing vs. plan: a quick top-bar dropdown and a "Loaded: X" toast (no
  toast primitive exists yet).
- **1.3 Contextual tooltips** — 🟡 **Partial.** Every schema param renders a `?` info
  bubble with hover/tap tooltip from `param.help` (`.info[data-tip]` in `styles.css`,
  mobile tap-focus handled). Infra is done and mobile-aware. Missing: richer
  "why you'd use it" copy for `mode`, `satb-style`, `voicing`, `--perc-fill-rate` —
  a help-text content audit in the schema, not new UI.

## Phase 2 — Feedback & progress

- **2.1 Progress indicator** — 🟡 **Partial.** A status lamp + text
  (`loading`/`generating`/`ready`/`error`) already renders and requests are
  race-guarded by `reqIdRef`. Missing: an elapsed-time counter, spinner, and the
  ">5s, please wait" reassurance. In-process generation is fast, so a client-side
  elapsed timer suffices — no SSE/WebSocket needed.
- **2.2 Error feedback** — 🟡 **Partial.** The backend already wraps generation in
  `GenerationError` and returns structured `detail` (never raw stack traces —
  `generator_api.py`, `backend/app.py`); the frontend surfaces `j.detail`. Missing:
  a friendly toast/alert with a collapsible "Details" instead of the raw
  `<pre class="errbar">`.

## Phase 3 — Documentation

- **3.1 Instrument user guide** — 🟡 **Partial.** `docs/how-to/use-the-web-instrument.md`
  exists but is dev-focused (how to run Vite/uvicorn). Needs an end-user rewrite (what
  each knob does, exporting MIDI, troubleshooting silence). Screenshots TBD.
- **3.2 ChordBuilder quick start** — ❌ **Missing.** No `docs/how-to/use-chordbuilder.md`;
  closest is `write-chord-progressions.md` (grammar, not the tool).

## Phase 4 — Polish

- **4.1 Reset to defaults** — 🟡 **Partial.** A "+ New" button exists but resets to
  `SEED_OVERRIDES`, not pure argparse defaults, and has no confirm.
- **4.2 Keyboard shortcuts** — ❌ **Missing.** No global key handlers (only per-field
  Enter-to-commit); no `?` help overlay.
- **4.3 Token field UX** — 🟡 **Partial.** Token fields are already rich
  (`HarmonyEditor`, `PercField`/`PercList`, groove pickers, live parse validation).
  Missing: a "Syntax Help" side-panel link and focus hints.
- **4.4 Settings export/import** — ❌ **Missing.** Presets persist server-side, but no
  JSON file export/import for sharing configs.

## Phase 5 — ChordBuilder positioning

- **5.1 Link to ChordBuilder** — ✅ **Done.** Top-nav has Chords + ChordBuilder links,
  footer repeats them. Missing only exact tooltip copy.
- **5.2 Cross-link back** — ✅ **Done.** chords-frontend footer links "full instrument"
  back to the main app. Missing only param-passing (`?chords=…`) and a tooltip.

## Re-prioritized work

Highest value / genuinely missing, smallest surface:

1. **Reusable Toast primitive** — unlocks 1.2 (load confirmation) and 2.2 (friendly
   errors) at once; it's the missing building block.
2. **2.2 friendly error surface** — swap the raw `<pre>` for a toast + collapsible
   details.
3. **2.1 elapsed timer** — a few lines on top of existing status state.
4. **1.3 + 3.1 content passes** — enrich schema `help` text; rewrite the user guide.
   No new UI, high clarity payoff.
5. **1.1 welcome overlay** — nice, but lowest urgency (app already boots into audible
   music).

Skip as redundant: the `/api/presets/list` endpoint and a top-bar demo dropdown (the
Library tab covers both). Treat Phase 5 as done bar tooltip tweaks.

*Items 1–3 are implemented in the same change that adds this note.*
