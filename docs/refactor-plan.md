# Refactor & hardening plan — tightening the loose screws

Full audit of the codebase's debt, fragility, duplication, and inconsistency,
with a prioritized remediation plan. Goal: a solid, testable, maintainable
foundation before adding more musical features.

Snapshot: `music_generator.py` is **3,453 lines** (does everything); supporting
modules `melody/fugue/process/arrangement.py` (~90–255 lines each); `play_music`
is a **497-line zsh** wrapper; **101 tests** (all unit-level on builder
functions). Working tree clean.

---

## Findings

### A. Fragility / robustness
1. **`play_music` (497-line zsh wrapper)** — the single most fragile piece;
   already caused 3 bugs this session (PATH-dependent tool detection, bare `rm`,
   192 kHz loudnorm). It orchestrates generate → FluidSynth → ffmpeg → metadata →
   playback in shell: hard to test, PATH-sensitive, and it re-implements metadata
   writing that overlaps the Python side.
2. **Duplicated render/dispatch in `main()`** — the `--fugue`, `--process`, and
   `--song` paths each separately: build a slug/dir/path, create `MidiOut`, run a
   dispatch loop, `flush_to_end`, `save`, print "Wrote". ~4 near-identical copies.
3. **No integration/smoke test on the render paths** — all 101 tests are
   unit-level on builder functions. `main()`'s flat render (ostinato/mixed) and
   the fugue/process/dense/song CLI paths are **never exercised end-to-end**, so
   they can regress silently (the refactors below are riskier without this).

### B. Duplicate / dead code
4. **`key_roots` has its chain-repetition logic written twice** (≈lines 1425 &
   1461, "placeholder" vs "fallback for direct bracket") — a latent bug-farm in a
   core parser.
5. **`build_chord_timeline` vs `build_dense_timeline`** — overlapping loop
   structure (low priority; could parameterize the realizer).
6. **`logging_config`** — the `log_function_call` decorator is never used; the
   structured helpers (`log_file_operation`, `log_music_generation`) add little
   signal. Trim.
7. **Catalog system is half-built** — `update_master_catalog()` runs on every
   render (writes `output/master_catalog.json`) and `query_catalog.py` reads it,
   but it's undocumented and unverified. Finish it or remove it.
8. **Helper scripts** (`cleanup_audio`, `recreate_audio`, `view_logs`,
   `query_catalog`) — import OK, but unused/untested and overlap `play_music`.
   `recreate_audio.py:24` has a bare `except:`. Audit: keep/fix/remove.

### C. Structural (the monolith)
9. **`music_generator.py` does everything** — DSL parsing, music theory,
   voicing, the `MidiOut` writer, percussion, CLI, `main()`, catalog. 3,453 lines.
10. **`main()` is huge** — arg parsing + 4 mode branches + the flat render path
    inline. Hard to follow.

### D. Output layout / config inconsistency
11. **Two metadata locations:** `play_music` writes run metadata to top-level
    `metadata/<slug>/`, while `music_generator` creates `output/metadata/`
    (≈unused) and writes `.args.json` sidecars next to the MIDI. Three
    conventions for "metadata."
12. **`output/audio/` historically held MIDI** (legacy naming); **`output/library/`**
    is created but always empty.
13. **`config/` empty dir** coexists with the real `config.json` at root — dead.

### E. Hygiene
14. **Bare `except:`** in `recreate_audio.py`.
15. **No `make test` / lint config / dev-setup beyond the README** — minor.

---

## Plan (tiered by value ÷ risk)

### Tier 1 — Safety net + quick wins (do first; low risk)
- **1.1 Integration tests** for every render path: flat `--mode ostinato`/`mixed`,
  `--voicing dense`, `--fugue`, `--process`, `--song`. Each invokes the real
  code and asserts a valid, non-empty MIDI. *This guards every refactor below.*
- **1.2 De-dup `key_roots`** — collapse the two chain blocks into one helper.
- **1.3 Fix the bare `except:`** in `recreate_audio.py`.
- **1.4 Remove dead dirs** — `config/`, `output/library/`; stop creating unused
  `output/library`.

### Tier 2 — Kill the render duplication, then de-shell
- **2.1 Factor `render_events(events, out_path, *, bpm, programs, total, …)`**
  and `resolve_out_path(slug)` — replace the 4 copied dispatch/path blocks in
  `main()` (and reuse from arrangement). One render path.
- **2.2 Port `play_music` → Python `render.py`** — generate → FluidSynth → ffmpeg
  (normalize/boost) → metadata, with absolute-path tool detection. Keep a thin
  `play_music` shim that calls it (back-compat). Removes the most fragile code
  and the duplicate metadata logic.
- **2.3 Consolidate output layout** — one convention: `output/{midi,audio,metadata}/<slug>/`.
  Migrate `play_music`'s top-level `metadata/` into it.

### Tier 3 — Break up the monolith (FINALIZED PLAN, not yet executed)

Status: Tier 1 ✅ and Tier 2 ✅ are done. Tier 3 below is the agreed plan.

Decisions (locked): **re-export for backward compat** (slim `music_generator.py`
does `from <mod> import *` so the sibling modules keep using `mg.X` unchanged —
migrate their imports in a later optional pass); **~7 modules**; docs =
**module docstrings + `docs/architecture.md`** (see Documentation pass below).

**Target module map** (dependency-layered; a module only imports ones above it):

| Module | Responsibility | Depends on |
|---|---|---|
| `mtheory.py` | `NOTE_TO_PC`, `DUR_MAP`, `GM_ALIASES`, voice ranges + channel consts, `ChordDef`, `parse_key_name`, `pc`, `clamp_to_range`, `nearest_in_register`, `resolve_instrument`, `load/get_chord_recipe` | (none internal) |
| `percussion.py` | drum map (`load/set/get_drum_map`), perc-token parsing (`parse_single_token`/`parse_pattern`), `PercHit/PercStage/PercPlan`, drum timelines, `make_percussion_plan` | mtheory |
| `tokens.py` | chord DSL: `parse_colon_key_token`, `key_roots` (+ `_normalize_key_token`/`_emit_*`), `parse_repetition_token`, `parse_chain_repetition` | mtheory |
| `voicing.py` | `realize_SATB` (+`pick_soprano`/helpers), `realize_dense`, `build_bass_line`, `build_arpeggio_events`, `build_counterpoint_lines` | mtheory |
| `midiout.py` | the `MidiOut` writer class | mtheory |
| `composition.py` | `build_progression` + chord-family pickers, `build_chord_timeline`, `build_dense_timeline`, `build_harmony_events` | mtheory, tokens, voicing, percussion |
| `music_generator.py` (slim) | CLI/`main`, manifest+catalog, `render_events`/`resolve_out_path`/`_render_generated`/`_apply_melody`, project paths; re-exports all the above | everything |

**Execution sequence** (one module per commit; after each: run all 116 tests +
a functional render, then commit):
1. extract `mtheory.py`  2. `percussion.py`  3. `tokens.py`  4. `voicing.py`
5. `midiout.py`  6. `composition.py`  7. slim `music_generator.py` + module
docstrings  8. Documentation pass (below).

**Invariants / gotchas:** bottom-up order ⇒ no circular imports; perc-token
parsing stays *with* the drum map in `percussion.py` so `tokens.py` needn't
depend on it; the two module-level caches (`_CHORD_RECIPES_CACHE`,
`_ACTIVE_DRUM_MAP`) move with their functions and must exist in exactly one
place; `import *` re-exports only public names (verified the siblings only use
public `mg.*`).

**Documentation pass (Step 8):** a module docstring on each new module
(responsibility + deps); a keystone **`docs/architecture.md`** (this module map,
the dependency layering, and the data-flow pipeline CLI → tokens → composition →
voicing → MidiOut → render); a README architecture section; and a docstring
sweep on public functions that still lack one.

### Tier 4 — Decide & document
- **4.1 Catalog:** finish (`query_catalog` robust + documented, surfaced in
  README) **or** remove (`update_master_catalog` + `query_catalog.py`).
- **4.2 Helper scripts:** keep/fix/remove `cleanup_audio`/`recreate_audio`/
  `view_logs` (likely fold into `render.py`/CLI subcommands).
- **4.3 Trim `logging_config`** to what's used.
- **4.4 Add `make test` / a lint config** (ruff) + a short dev-setup doc.

---

## Suggested order
Tier 1 (safety net) → Tier 2.1 (de-dup render) → Tier 2.2/2.3 (de-shell +
layout) → Tier 3 (extract modules) → Tier 4 (decide/cleanup). Tiers 1–2 give the
biggest robustness gain for the least risk; Tier 3 is the long game, made safe by
Tier 1's tests.
