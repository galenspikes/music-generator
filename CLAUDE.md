# music-generator — agent orientation

A Python MIDI generator: a token DSL for chords/percussion → harmony + voices +
percussion → MIDI, optionally rendered to audio via FluidSynth. Modes include
ostinato grooves, arrangements (YAML song files), fugues, and process music.

## Start here — read these docs before working
The docs follow the [Diátaxis](https://diataxis.fr/) layout; **`docs/index.md`** is
the map. Key entry points:
- **`docs/explanation/architecture.md`** — module map, dependency layering, data
  flow. *(Read first to know where code lives.)*
- **`docs/design-notes/refactor-plan.md`** — the active code-health plan (monolith
  breakup + hardening), tiered, with status. **Check this before refactoring.**
- **`docs/reference/token-grammar.md`** — the chord/percussion/melody mini-languages
  (the project's core asset). Read before touching any parser.
- **`docs/design-notes/roadmap-phase2.md`** — feature roadmap (arrangement,
  melody/lead, mix).
- Design notes live in `docs/design-notes/` (arrangement, melody-primitive,
  leadsheet-import). Worked songs: `songs/*.yml`, `docs/reference/charts.md`.

## Dev workflow
- Env: `python3 -m venv venv && venv/bin/pip install -r requirements.txt`
  (dev: `requirements-dev.txt`). Audio needs `brew install fluidsynth ffmpeg`.
- **Tests: `venv/bin/python -m pytest`** — run before AND after any change.
  The `tests/test_integration.py` smoke tests guard every render mode; the token
  tests pin the DSL. Treat them as the safety net for refactors.
- Generate (MIDI only): `venv/bin/python music_generator.py --mode ostinato --keys '...' --out NAME --no-play`
- Render audio: `./play_music --save-wav --sf2 SoundFonts/arachno.sf2 ... ` (thin
  shim over `render.py`).
- Output lands in `output/{midi,audio,metadata}/<slug>/`. `output/`, `metadata/`,
  `SoundFonts/`, and `songs/*.pdf` are gitignored.

## Conventions
- Commit/push only when asked; one logical change per commit; keep tests green.
- The token DSL is the crown jewel — never edit a parser without running the token
  tests, and update `docs/reference/token-grammar.md` if the grammar changes.
- Big binaries (SoundFonts) and generated output are never committed.
