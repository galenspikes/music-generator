# Web token builder — design plan

A touch-first visual composer for the chord/percussion **token DSL**, for the
PWA (`web/`). Goal: let a musician build complex tokens, groups, and whole
charts by tapping, dragging, and dropping — while staying 100% interoperable
with the text tokens (copy/paste in and out).

## Principles
1. **Text is the source of truth.** The builder is a *view* over the token
   string. Power users keep the raw field; copy/paste must round-trip exactly.
   `parse(serialize(x)) === x` and `serialize(parse(s))` normalizes `s`.
2. **Mobile-first.** Big tap targets (≥44px), bottom-sheet editors for thumb
   reach, horizontal chip strip, no hover-only affordances.
3. **Engine parity.** Dropdown vocab (the 81 recipes) is generated from
   `library/chord_recipes.py` at build time → `web/recipes.json`, so the UI can
   never drift from the engine. (New `tools/dump_recipes.py`.)
4. **Never trap the user.** Anything the visual editor can't represent falls
   back to the raw text field instead of erroring.

## Data model
```
Chord = { root, inversion?, recipe?, bass?, repeat? }   // A:1:min9/C ×N
Group = { children: Chord[], repeat }                    // [ ... ]*N
Chart = (Chord | Group)[]
```
A small JS tokenizer/serializer mirrors the Python grammar in
`docs/token-grammar.md` (colon tokens `root[:inv][:recipe][/bass]`, `*N`
repetition, `[..]*N` groups). It's lenient: an unparseable token is kept as a
raw chip so paste of anything still works.

## UI (chord mode) — mock
```
┌───────────────────────────────────────────────┐
│  ▤ Cmaj9   ▤ A·min11   ▤ D·min9   ▤ G13   [＋]  │   ← draggable chip strip
│                              (drag to reorder)  │
├───────────────────────────────────────────────┤
│  Editing: chip 2                       ✕ delete │
│  Root   [ A ▾ ]                                 │
│  Quality[ min11 ▾ ]  (grouped: 7ths/9-11-13/…) │
│  Invers [ root ▾ ]   Bass [ none ▾ ]            │
│  Repeat [ – 1 + ]    ⧉ duplicate   ▶ preview    │
├───────────────────────────────────────────────┤
│  Tokens:  C::maj9, A::min11, D::min9, G::13     │  ← live, editable, ⧉ copy / paste
└───────────────────────────────────────────────┘
```
- Tap a chip → bottom-sheet editor (root / quality / inversion / bass / repeat).
- `＋` adds a chip; long-press a chip → duplicate/delete; drag handle reorders.
- The **Tokens** field is always in sync; editing it re-parses into chips.
- **Copy** exports the string; **Paste** imports (so charts move between the app,
  the CLI, and the gallery freely).

## Recipe palette
Group the 81 recipes into friendly sections, most-common pinned:
Triads · 6/7ths · 9·11·13 · Suspended · Altered dominants · Quartal/Quintal ·
Clusters · Aug-6ths/Neapolitan · Spectral/Exotic (mystic, messiaen…, petrushka,
whole-tone, octatonic). Generated from the engine so it's always complete.

## Interaction tech
- **Drag-and-drop:** Pointer Events (not HTML5 DnD — poor on touch) with a
  transform-follow ghost and an insertion marker. Works mouse + touch.
- **Bottom sheet:** a CSS sheet that slides up; native `<select>` for the wheels
  (best mobile UX, zero deps).
- No frameworks — keep the PWA dependency-free (vanilla JS modules), matching the
  current app.

## Phasing
- **Phase 1 — Chord chip builder** *(highest value, self-contained)*: parser +
  serializer, chip strip, bottom-sheet editor, reorder, repeat stepper,
  copy/paste, raw-field sync. `recipes.json` build step.
- **Phase 2 — Groups**: select chips → wrap in `[..]*N`; bracket container UI.
- **Phase 3 — Percussion grid**: step sequencer (instruments × steps), per-cell
  velocity/probability/flam via long-press → percussion tokens; bar length +
  subdivision controls.
- **Phase 4 — Melody**: scale-degree grid/piano-roll for `--melody` tokens.
- **Phase 5 — Fun**: drag progressions in from the demo gallery; "favorite"
  chips; haptics; chord audio preview on tap.

## Open questions
- Inline per-token audio preview (tap a chip to hear it) — nice but needs a quick
  one-chord render path; defer to Phase 5.
- How much of the percussion `[vel/prob/flam]` modifier syntax to surface in the
  grid vs. keep text-only (lean: long-press reveals it).
```
