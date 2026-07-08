# Roadmap — toward an EP of generative grooves

Planning doc; some threads are now shipped (marked inline). North star: produce
release-quality, long-form grooves from charts, finished in a DAW. Four
threads, each with a concrete design. Cross-cutting enabler called out at the
end.

Current foundation: per-voice channels (split stems), per-voice instruments,
independent bass generator, arrangement layer Phase 1 (YAML sections, per-section
tempo/instruments, `build_harmony_events`, `MidiOut.set_tempo_at` /
`program_change_at`). Tests: 64 passing.

---

## Thread 1 — Arrangement Phase 2 (make sections feel composed)

**Goal:** sections that connect musically, breathe dynamically, and can be
arranged into real song forms without copy-paste.

### 1a. Form references (DRY song structure) — SHIPPED
Define sections once, sequence by name:
```yaml
blocks:
  verse:  { keys: "...", bass: {style: root} }
  chorus: { keys: "...", bass: {style: octaves}, voices: {soprano: saw} }
form: [verse, chorus, verse, chorus]
```
`build_spec` expands `form` → the flat `sections` list, with optional inline
`{block_name: overrides}` per occurrence (e.g. a louder second chorus).
`form`/`blocks` and plain `sections` are both supported; `form` wins if both
are present. See [create-an-arrangement.md](../how-to/create-an-arrangement.md).

### 1b. Cross-section continuity — SHIPPED
Each section no longer starts voicing fresh: `arrangement.build_events` threads
the soprano lead-in and bass register anchor from the end of section N into
the start of section N+1 via `build_chord_timeline(..., prev_sop=, bass_anchor=)`
/ `realize_SATB(..., bass_anchor=)` (both default to the old behavior, so the
flat single-render path is unaffected).

### 1c. Transitions / fills at boundaries — SHIPPED
Per-section `transition: {fill: 1bar, crash: true}`:
- `fill` replaces the last N bars of the section's drum timeline with a fill
  drawn from `perc.interrupters` (falls back to the main pattern),
- `crash` adds a crash-cymbal hit on the next section's downbeat (skipped on
  the last section).
Hard cut remains the default when `transition` is unset.

### 1d. Dynamics arc — SHIPPED
Per-section `dynamics: {intensity}` → base velocity + density:
```yaml
verse:  { dynamics: {intensity: 0.6} }
chorus: { dynamics: {intensity: 1.0} }
```
`render_events` gained an `intensity_at(when_beats)` lookup (default: constant
1.0, so the flat render path is unaffected) that scales the base velocity
passed to `play_voice_note`/`chord_block`/`dense_block` and the new `vel_scale`
on `MidiOut.drums_block`; `arrangement.intensity_lookup(spec)` builds it from
each section's beat range without touching the RNG (so it can run alongside
`build_events` on the same spec). Percussion density scales separately, in
`build_events`, by multiplying each section's `perc.fill_rate` by its
intensity. See [create-an-arrangement.md](../how-to/create-an-arrangement.md).
Optional global build curve (continuous rather than per-section step) is
still open for a later pass.

### 1e. `seconds:` length target
`length: {seconds: 1200}` → after one pass of the form, repeat/trim the whole
form to hit the target. (Per-section tempo means beats→seconds varies, so
compute each section's seconds from its tempo and accumulate.)

**Open questions:** fill source (auto from interrupters vs a dedicated fill
field)? intensity as one scalar vs explicit velocity/density? seconds-target =
loop whole form vs extend the last/outro section?

**Effort:** 1a small, 1b/1d medium, 1c/1e medium. **Risk:** low–medium.

---

## Thread 2 — Melody / lead generator (the hook)

**Goal:** a monophonic, motif-based lead — the part a listener hums. Today the
"lead" is just the SATB soprano; this is a dedicated generator.

### Design
- **Where it lives:** a 5th voice on its own channel (ch 4). Requires extending
  `MidiOut` beyond the 4 SATB voices (optional `lead` track/channel + program).
- **Pitch material:** per chord (from `chord_tl`) derive chord tones + a scale
  (chord-tone set, optionally widened to a mode). Strong beats favor chord
  tones; weak beats allow steps/passing tones; leaps resolve.
- **Rhythm:** draw from a small rhythm-cell pool (the percussion token grammar
  could even describe lead rhythms), with rests — silence is what makes a hook.
- **Phrasing/development:** state a motif, then develop it — repeat, transpose
  to fit the next chord, invert, sequence; antecedent/consequent over a 4/8-bar
  phrase; call-and-response (phrase, rest, answer).

### Surface
```yaml
lead: { instrument: sax, style: motif, density: 0.5, register: high, rests: 0.4 }
```
Per-section (lead only in chorus/solo), like other section knobs.

### Phasing
- **v1:** chord-tone motif with rests + repetition fit to each chord (sounds
  intentional, not noodly).
- **v2:** motif development (transpose/invert/sequence) + call-and-response.
- **v3:** scale-aware passing tones, proper phrase arcs, tension/release.

**Open questions:** scale source — derive from chord, or declare key/mode per
section? Lead as a true 5th channel vs repurposing soprano when active? Degree
of randomness vs a stated, developed motif?

**Effort:** large (most ambitious). **Risk:** medium — biggest musical payoff,
and the MidiOut 5th-voice change touches core.

---

## Thread 3 — Groove & feel

**Goal:** the micro-timing/velocity life that makes heads nod.

### Ideas
- **Swing/shuffle — SHIPPED (v1, global):** `--swing 0..0.75` warps off-beat
  subdivisions in `render_events` via `apply_swing`/`_swing_time` (0 = straight
  eighths, 0.5 = triplet swing). It reads `MidiOut.swing`, so it applies to
  every render path (flat, arrangement, fugue, process); songs set it under
  `defaults: { swing: ... }`. *Still open: per-section swing.*
- **Pocket / micro-timing:** small per-voice timing offsets — bass slightly
  ahead, snare laid back. Per-voice `timing_offset` in ms/ticks.
- **Bass locked to kick:** a bass style (or flag) that places bass onsets on the
  kick hits of the active drum pattern (bass generator reads the perc grid).
- **Ghost notes (drums):** auto-inject low-velocity snare/hat ghosts; the token
  DSL already supports `[vel-N]`/`[prob]`, so this is partly an auto-humanize.
- **Better humanization:** accent beat 1, velocity curves, tighter/looser feel
  per section.

### Phasing
- **v1:** swing + laid-back snare + accent-on-1 (contained, immediately audible).
- **v2:** bass-locked-to-kick + ghost notes.
- **v3:** per-genre feel presets.

**Open questions:** swing global vs per-section? expose raw timing offsets or
ship genre "feel" presets? bass-kick lock as a `--bass-style` vs a modifier on
existing styles?

**Effort:** v1 small–medium. **Risk:** low (transforms are localized), but feel
needs ear-tuning.

---

## Thread 4 — Mix & stems (release-quality output)

**Goal:** make renders sit right, and enable finishing in a DAW.

### 4a. Per-voice pan / volume — *pan SHIPPED*
CC7 (volume) already goes out per voice channel at init. **Pan is now live:**
`--pan-spread 0..1` emits CC10 per SATB voice from `VOICE_PAN_POS`
(soprano/bass widest, alto/tenor inside; 0 = mono/centred). Songs set it under
`defaults: { pan_spread: ... }`. *Still open: explicit per-voice pan/vol values
and per-section mixes, e.g.*
```yaml
mix: { bass: {vol: 105, pan: 64}, soprano: {pan: 84}, drums: {vol: 110} }
```

### 4b. Stems export — *the "actually releasable" feature*
Voices are already on separate channels/tracks. Render **per-stem WAVs** so you
mix/master externally. Two approaches:
- **Per-stem MIDI** (simple, DAW-friendly): write one MIDI per voice + drums;
  render each to WAV. Also directly importable into Logic/Ableton.
- **Channel-mute rendering:** one MIDI, render N times muting all but one
  channel. Fewer files but fiddlier with FluidSynth.
Recommendation: per-stem MIDI; pairs with the render port below.

### 4c. Per-section FX via CC
CC91 (reverb send) / CC93 (chorus send) per channel/section for spatial
dynamics without swapping soundfonts.

**Open questions:** stems as separate MIDI vs channel-mute render? expose pan/vol
per section or song-global only in v1? bounce stems to WAV here, or just emit
MIDI stems and mix entirely in the DAW?

**Effort:** 4a small, 4b medium (needs render orchestration), 4c small.
**Risk:** low.

---

## Cross-cutting enabler — port `play_music` → Python `render.py`

Threads 4b (stems), 4c (per-section FX), and album batch-rendering all get much
easier in Python than in the shell wrapper (which already cost us 3 bug fixes).
A `render.py` that does generate → FluidSynth → ffmpeg, with stem and batch
support, is the natural home. Worth doing before/with Thread 4.

---

## Thread 5 — Fugue lab (exploration + teaching)

The `--fugue` mode is only an *exposition* today (subject, tonal-ish answer,
inverted countersubject, cadence — see `fugue.py`), but it's the most-liked demo
and points at two futures worth pursuing:

- **A real fugue generator.** Grow past the exposition: episodes (sequenced
  fragments of the subject), middle entries in related keys, and the classic
  devices — stretto, invertible counterpoint, augmentation/diminution of the
  subject. The melody primitive already gives us `transpose_diatonic` / `invert` /
  `retrograde` / `augment` (`melody.py`), so the transforms are in hand; what's
  missing is the *form* controller that schedules entries and episodes.
- **An educational tool.** A guided "build a fugue" surface (in the webapp or a
  notebook): type a subject, watch each voice enter, and toggle each device on/off
  to *hear* what an episode or a stretto does. The scale-degree notation and the
  piano-roll make the structure legible — a genuinely good way to teach fugue.

**Effort:** generator medium–large; teaching UI medium. **Risk:** medium (real
fugal writing is hard to get consistently musical). **Why:** high-delight, and it
doubles as a showcase and a learning aid.

---

## Suggested sequencing toward the EP
1. **Quick wins:** Thread 4a (pan/volume) + Thread 3 v1 (swing/feel) — immediate
   audible upgrade to everything.
2. **Composition:** Thread 1a (form refs) → 1b (continuity) → 1c/1d
   (transitions, dynamics) — songs that hold together over 20 minutes.
3. **The hook:** Thread 2 v1–v2 (melody) — the biggest musical leap.
4. **Release:** `render.py` port → Thread 4b (stems) — finish in a DAW.

Groove polish (Thread 3 v2+) threads in throughout.
