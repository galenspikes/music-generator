# Design notes

*Forward-looking **plans**, kept deliberately separate from the truth docs. These
describe what is **intended or proposed**, which may differ from what exists today.
When a plan ships, fold the durable parts into Reference/Explanation and leave the
plan here as a record.*

## Contents

- **[ui-ux-roadmap.md](ui-ux-roadmap.md)** — the active UI/UX roadmap for the
  webapp instrument (presets, control-surface presentation, sound/instrument
  switching). **Start here for anything UI-facing.**
- **[roadmap-phase2.md](roadmap-phase2.md)** — feature roadmap (arrangement,
  melody/lead, mix). Fugue (Thread 5) is parked; see the instrument-first
  decision in [gap-analysis.md](gap-analysis.md).
- **[arrangement-plan.md](arrangement-plan.md)** — the arrangement-layer design.
- **[melody-primitive-plan.md](melody-primitive-plan.md)** — the scale-degree
  melody language design (includes the rationale for choosing degrees).
- **[leadsheet-import-plan.md](leadsheet-import-plan.md)** — lead-sheet → song.yml
  import. v1 (chord-symbol mapper + emitter) shipped — see `leadsheet.py` and
  [the how-to guide](../how-to/import-a-lead-sheet.md).
- **[refactor-plan.md](refactor-plan.md)** — the active code-health plan
  (monolith breakup + hardening). **Check this before refactoring.**
- **[webapp-ui-design.md](webapp-ui-design.md)** — the instrument UI/UX direction.
- **[ecosystem-navigation-plan.md](ecosystem-navigation-plan.md)** — unifying
  navigation across the showcase, web instrument, Space, and docs (records two
  broken-link bugs and a plan to fix them at the root).
