# Code Review Action Items

Generated: 2026-07-09  
Based on: Critical code review of music-generator repository  
Current grade: B+ (Strong execution + good tests, held back by debt + linting + scaling risk)

## IMMEDIATE (1–2 sessions) — Blocking issues

### Linting & Tests
- [x] **Fix E402 import order** (`webapp/backend/app.py:35`)
  - Move `mimetypes.add_type()` call after all imports, or wrap in function
  - **Effort:** 5 min
  - **Priority:** P0 (CI gate)

- [x] **Resolve duplicate test classes (F811)**
  - Merge `TestParameterSchema` definitions in `test_generator_api_comprehensive.py` (lines 327 & 523)
  - Merge `TestVelocityComputation` in `test_midiout_comprehensive.py` (lines 108 & 410)
  - Currently second definition shadows first; tests may not run as intended
  - **Effort:** 15 min
  - **Priority:** P0 (Test coverage integrity)

- [x] **Remove unused imports (F401)** — 9 instances
  - Run `ruff check --fix .` to auto-fix F401, F841
  - Manually verify fixes don't change behavior
  - **Effort:** 10 min
  - **Priority:** P1 (Hygiene)

- [x] **Fix bare `except Exception` in `generator_api.py:89`**
  - Only catch specific exceptions; document why/what's expected
  - Current: silently swallows all errors
  - **Effort:** 5 min
  - **Priority:** P1 (Error handling)

---

### Error Handling
- [x] **Replace regex-based error classification**
  - Current: `classify_error()` pattern-matches raw error messages (brittle)
  - Proposal: Raise specific exception types (`InvalidKeyError`, `InvalidRecipeError`, etc.)
  - Map exception type → (error_type, suggestion, code) in a registry
  - **Modules affected:** `tokens.py`, `percussion.py`, `composition.py`
  - **Effort:** 2–3 hours
  - **Priority:** P1 (Fragility)

---

## SHORT-TERM (1–2 weeks) — Code quality

### Documentation
- [x] **Add docstrings to top 20 functions**
  - Priority: `voicing.realize_SATB()`, `composition.build_progression()`, `midiout.MidiOut.chord_events()`
  - Target: Complex functions >50 lines without docstrings
  - Use ruff rule to identify (e.g., `ruff rule ARG002`)
  - **Effort:** 3–4 hours
  - **Priority:** P2 (Onboarding)

- [x] **Create PUBLIC_API.md**
  - Document stable functions vs. internal helpers
  - Clarify which re-exports from `music_generator.py` are guaranteed
  - **Effort:** 1 hour
  - **Priority:** P2 (API clarity)

- [x] **Document error codes** (docs/reference/error-codes.md)
  - Central registry of error codes (ERR_CHORD_001, etc.)
  - Map to error_type, suggested fix, remediation steps
  - **Effort:** 30 min
  - **Priority:** P3 (UX polish)

### Refactoring
- [x] **Extract parameter validation into a class**
  - Reduce `generator_api.py` (1,110 lines) complexity
  - Create `ParameterSchema` class to hold validation logic
  - **Effort:** 2–3 hours
  - **Priority:** P2 (Maintainability)

- [x] **Add function to warn on silent file overwrites**
  - Current: MIDI files silently overwritten if they exist at output path
  - Proposal: Add `--overwrite` flag; warn by default
  - **Effort:** 30 min
  - **Priority:** P2 (UX)

- [x] **Fix `fill_chords_to_end()` mutation**
  - Current: Mutates input list in-place; callers may not expect this
  - Proposal: Return new list instead (functional style)
  - **Effort:** 15 min
  - **Priority:** P2 (API clarity)

---

## MEDIUM-TERM (1–2 months) — Structural debt (Tier 4 refactor)

### Module Extraction
- [x] **Split `percussion.py` (704 lines)** — `percussion.py` kept as the
      public façade; internals now live in map/tokens/timeline layers
  - Create `percussion_map.py` (drum map management: load/set/get)
  - Create `percussion_tokens.py` (token parsing: parse_single_token, parse_pattern)
  - Create `percussion_timeline.py` (timeline building: build_drum_timeline_*)
  - Update imports in `composition.py`, `midiout.py`
  - **Effort:** 4–6 hours
  - **Priority:** P2 (SRP, testability)

- [x] **Extract error classification into a class**
  - Done via the exception registry option: `errors.py` types +
    `generator_api._EXC_SUGGESTIONS` / `classify_exception()` dispatch
  - Move `classify_error()`, `_drum_letter_crib()`, `_classified()` logic
  - Replace regex matching with exception type dispatch
  - **Effort:** 2–3 hours
  - **Priority:** P2 (Fragility, reusability)

- [x] **Refactor `generator_api.py` into classes**
  - `ParameterSchema` — introspect and validate CLI args
  - `ErrorClassifier` — classify errors + generate suggestions
  - `ResultSerializer` — convert internal structures to API DTOs
  - Keep `generate()`, `validate()` as module-level facades
  - **Effort:** 6–8 hours
  - **Priority:** P2 (Clarity, testability)

### Testing
- [x] **Add docstring-based tests for complex functions**
  - Functions >50 lines should have usage examples in docstrings
  - Example: `voicing.realize_SATB()` docstring should show how to use it
  - Done alongside the docstring pass: realize_SATB, build_counterpoint_lines,
    build_progression, MidiOut.__init__/chord_block/drums_block carry examples
  - **Effort:** 2–3 hours
  - **Priority:** P3 (Documentation)

- [x] **Add property-based tests for token parsing**
      (tests/test_tokens_properties.py, hypothesis)
  - Use hypothesis to generate random valid/invalid tokens
  - Verify parser handles all edge cases consistently
  - **Effort:** 3–4 hours
  - **Priority:** P3 (Robustness)

---

## LONG-TERM (Tier 5 refactor) — Scaling & concurrency

### Global State Elimination
- [ ] **Refactor drum map into dependency injection**
  - Pass `DrumMap` class (or dict) through builder functions
  - Remove `_DRUM_MAP_CACHE`, `set_active_drum_map()`, `get_drum_map()` global state
  - Builders: `build_perc_from_args(drum_map=None)` instead of relying on global
  - **Effort:** 8–12 hours
  - **Priority:** P1 (Critical blocker for multi-worker scaling)

- [ ] **Refactor RNG into context parameter**
  - Pass RNG instance through builders instead of using global `random`
  - Allows deterministic generation + parallel execution without interference
  - **Effort:** 4–6 hours
  - **Priority:** P1 (Testability, reproducibility)

- [ ] **Refactor chord-recipe cache**
  - Move `_CHORD_RECIPES_CACHE` into a context-managed class
  - Allow multiple concurrent loads without races
  - **Effort:** 2–3 hours
  - **Priority:** P1

### Deployment & Scaling
- [ ] **Support multi-worker FastAPI deployment**
  - Once global state is eliminated, test with multiple workers
  - Add concurrency tests to CI
  - **Effort:** 2–3 hours
  - **Priority:** P1 (Production requirement)

- [ ] **Add structured logging at error boundaries**
  - Log timestamp, spec hash, error code, stack trace at `generator_api.generate()`
  - Enable debugging prod issues without verbose debug mode
  - **Effort:** 2–3 hours
  - **Priority:** P2 (Observability)

---

## NICE-TO-HAVE (Lower priority)

- [ ] Add performance benchmarks (target: <100ms per generation)
- [ ] Property-based fuzzing of full MIDI generation pipeline
- [ ] Support in-process audio synthesis (remove FluidSynth dependency for web)
- [ ] Async generation support in web API
- [ ] Database for saved progressions (ChordBuilder feature)

---

## TRACKER

| Category | Count | Status |
|----------|-------|--------|
| P0 (Blocking) | 3 | ⏳ Not started |
| P1 (High) | 7 | ⏳ Not started |
| P2 (Medium) | 12 | ⏳ Not started |
| P3 (Low) | 5 | ⏳ Not started |
| **Total** | **27** | — |

---

## NOTES

- **Why now?** Code review completed 2026-07-09; project is shipping (Hugging Face Space deployed), but has known scaling limitations.
- **Why this priority order?** Immediate items unblock day-to-day work; short-term improves quality; medium-term enables scaling; long-term is architectural.
- **Risk:** Global state elimination (Tier 5) is highest risk; needs comprehensive testing. Recommend doing it incrementally (drum map → RNG → chord recipes) with a new test suite for concurrent generation.
- **Dependencies:** Error classification refactor should precede API refactor (both touch error boundaries).

---

## REFERENCE

- Full review: See `docs/` or shared `code-review.md`
- Refactor plan: `docs/design-notes/refactor-plan.md` (Tiers 1–4 complete; Tier 5 is the next frontier)
- Architecture: `docs/explanation/architecture.md`
