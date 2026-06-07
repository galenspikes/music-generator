# Lead sheet PDF → music-generator script — design plan

Planning doc. Goal: take a lead sheet PDF and produce a **song.yml** (sections +
chords) for the arrangement layer.

**Decisions (locked):**
- PDFs are a **mix** of born-digital and scans → **agent-assisted vision
  extraction is the primary path** (robust to both); the deterministic
  text-layer parser is a later fast-path for born-digital PDFs.
- Output is **song.yml** (arrangement), not a flat `--keys` string.
- **Chords/form only** — no melody/OMR.

So v1 = a documented **agent extraction workflow** that produces the IR, plus a
real, tested **`chordsym_to_token` mapper** and an **IR → song.yml emitter**
(the durable, reproducible core).

## The pipeline (3 stages)
```
PDF ──(1) extract──> normalized chart ──(3) map──> song.yml / --keys
        │                  (IR)                       │
        └ chords, form, key, tempo, (melody)          └ chord-symbol → DSL token
```
The middle **normalized chart** is the key design idea: a small intermediate
representation (IR) that decouples *how we read the PDF* from *how we emit the
script*. Any extractor can target the IR; one emitter consumes it.

---

## Stage 1 — extraction (the hard part; pick by PDF type)

Three options, honestly assessed:

### A. Text-layer extraction — *best when the PDF is "born-digital"*
Many lead sheets exported from notation software / chord sites have a real text
layer: the chord symbols are **text with x/y positions**. `pdfplumber` /
`pymupdf` give words + coordinates; reconstruct the chart by reading lines
left→right, grouping into measures, separating chord-rows from lyric-rows by
font/position.
- ✅ Exact for the chord *symbols*; no ML; reproducible.
- ❌ Gets chords/lyrics/section labels, **not the melody** (noteheads are vector
  graphics, not text). Fails on scanned/image PDFs (no text layer).

### B. Vision model (Claude reads the page) — *best for image/scanned PDFs & form*
Render pages to images and have a multimodal model transcribe the chart into the
IR (sections, chords, repeats, key, tempo). **This is unusually available here:
Claude Code's Read tool already reads PDFs** — so a v1 can be a *workflow*, not a
big build: "read this lead sheet, emit song.yml using docs/token-grammar.md."
- ✅ Handles image PDFs, messy layouts, section/repeat structure, capo notes.
- ✅ Near-zero code to start (a documented prompt/skill).
- ❌ Needs human verification (hallucination risk); not deterministic.

### C. Optical Music Recognition (OMR) — *only if we want the melody*
Tools like `oemer` (DL-based, Python) or Audiveris output MusicXML; parse with
`music21` → chords + melody.
- ✅ The only path that recovers the **melody** (notes/rhythm).
- ❌ Hard and error-prone, especially on scans/handwriting; heavy deps; chord
  *text* often recognized worse than noteheads. High effort, variable payoff.

**Recommendation:** start with **B** (agent-assisted, available now) + build the
deterministic **Stage 3 mapper** (below) as the reusable core. Add **A** as a
fast exact path for born-digital PDFs. Treat **C / melody** as a stretch.

---

## Stage 2 — normalized chart (intermediate representation)
A small JSON/dict any extractor produces and the emitter consumes:
```yaml
title: ...
key: Bb            # concert key (or note capo)
tempo: 132
time: 4/4
sections:
  - name: A
    repeat: 2
    measures:
      - ["Bbmaj7", "G7"]      # chords per measure (beats inferred or explicit)
      - ["Cm7", "F7"]
  - name: B
    measures: [ ... ]
melody:              # optional (only if OMR/vision gets it)
  - {section: A, notes: "q1 q3 ..."}   # in the melody scale-degree grammar
```
Decouples extraction from emission; easy to hand-edit/verify.

---

## Stage 3 — chord-symbol → DSL mapping (the reusable, testable core)
A `chordsym_to_token(symbol)` translator from lead-sheet notation to our colon
tokens. This is the piece worth building well regardless of extractor, and our
existing vocabulary already covers most of it:

| Lead sheet | Token |
|---|---|
| `C`, `Cmaj`, `CM` | `C::maj` |
| `Cm`, `Cmin`, `C-` | `C::min` |
| `C7` | `C::7` |
| `Cmaj7`, `CM7`, `CΔ` | `C::maj7` |
| `Cm7`, `C-7` | `C::min7` |
| `Cm7b5`, `Cø` | `C::m7b5` |
| `Cdim`, `C°` / `Cdim7`, `C°7` | `C::dim` / `C::dim7` |
| `Caug`, `C+` | `C::aug` |
| `Csus4`, `Csus2`, `C7sus4` | `C::sus4` / `C::sus2` / `C::sus4add7` |
| `C6`, `Cm6` | `C::majadd6` / `C::minadd6` |
| `C9`, `Cmaj9`, `Cm9`, `C11`, `C13` | `C::9` / `C::maj9` / `C::min9` / `C::11` / `C::13` |
| `C7b9`, `C7#9`, `C7#11`, `C7alt` | matching recipes |
| `C/E` (slash) | `C::maj/E` |

Plus: **transpose / capo** handling (the Kiss chart needed +3); a measure→
duration policy (e.g. one chord/bar → `--chord-length w`, two → `h`); and
**sections → song.yml** (the arrangement layer is the natural target, and `A B`
forms map to `form: [...]`). Unknown symbols → a clear warning + best-effort
fallback, never a silent guess.

---

## Melody (optional, hard)
If we ever get the melody (OMR or a careful vision pass), it maps to the
**melody primitive**: notes → scale degrees in the chart's key → a `--melody`
line, or a **fugue subject**. Nice tie-in, but gated on reliable note
extraction. Out of scope for v1.

---

## Verification (non-negotiable)
Every path emits a **human-readable song.yml the user reviews and edits** — not a
one-shot render. Round-trip aid: print the parsed chart back as readable chords
so mistakes are obvious. Optionally render a quick MIDI to sanity-check.

---

## Phasing (per the locked decisions)
- **v1 — agent workflow + deterministic core:**
  1. `chordsym_to_token(symbol) -> token` mapper (real, tested; handles
     qualities, extensions, slash bass, transpose).
  2. IR schema + `ir_to_song_yml(ir)` emitter (measures→chord-length, sections→
     `form`/`blocks`, concert-key transpose).
  3. A documented extraction workflow/skill: Claude reads the PDF (Read tool) →
     fills the IR → calls the emitter → user reviews the song.yml.
- **v2:** deterministic text-layer extractor (`pdfplumber`) for born-digital
  PDFs → IR, no LLM in the loop (fast, exact, reproducible).
- **v3 (stretch):** OMR for melody → `--melody`/fugue subject.

## Resolved
PDFs = mix → vision/agent primary. Output = song.yml. Melody = out of scope.
Remaining detail to settle when building: measure→duration policy (chords/bar →
`--chord-length`), and how aggressively to infer `repeat`/`form` vs leave flat.
