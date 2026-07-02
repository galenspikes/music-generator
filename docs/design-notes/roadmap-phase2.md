# Roadmap — toward an EP of generative grooves

Planning doc (not yet implemented). North star: produce release-quality,
long-form grooves from charts, finished in a DAW. Four threads, each with a
concrete design. Cross-cutting enabler called out at the end.

Current foundation: per-voice channels (split stems), per-voice instruments,
independent bass generator, arrangement layer Phase 1 (YAML sections, per-section
tempo/instruments, `build_harmony_events`, `MidiOut.set_tempo_at` /
`program_change_at`). Tests: 64 passing.

---

## Thread 1 — Arrangement Phase 2 (make sections feel composed)

**Goal:** sections that connect musically, breathe dynamically, and can be
arranged into real song forms without copy-paste.

### 1a. Form references (DRY song structure) — *do first, pure loader change*
Define sections once, sequence by name.
```yaml
blocks:
  verse:  { repeat: 2, keys: "...", bass: {style: root} }
  chorus: { repeat: 2, keys: "...", bass: {style: octaves}, voices: {soprano: saw} }
form: [intro, verse, chorus, verse, chorus, solo, chorus, outro]
```
`build_spec` expands `form` → the flat `sections` list (with optional inline
overrides per reference). No engine change. High value, low risk.

### 1b. Cross-section continuity — *fixes the one rough edge in Phase 1*
Today each section starts voicing fresh. Thread state across boundaries:
- `build_chord_timeline` gains optional `prev_sop` in / final-sop out (default
  None keeps the flat path identical).
- bass register cursor carried between sections.
- `arrange()` passes the trailing state of section N into section N+1.

### 1c. Transitions / fills at boundaries
Per-section `transition: {fill: 1bar, crash: true}`:
- replace the last N beats of the section's drum timeline with a fill (reuse
  `build_drum_segment` at high fill-rate, or a named fill pattern),
- add a crash (`j`) on the next section's downbeat.
Hard cut remains the default.

### 1d. Dynamics arc
Per-section intensity → base velocity + density:
```yaml
verse:  { dynamics: {intensity: 0.6} }
chorus: { dynamics: {intensity: 1.0} }
```
Map intensity → chord/bass velocity base (currently fixed at 78) and scale
perc fill-rate. `build_harmony_events` / `play_voice_note` already take a `base`
velocity — plumb it through per section. Optional global build curve later.

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
- **Swing/shuffle:** delay off-beat subdivisions by a swing %. Implement as a
  transform on event `when` keyed to position within the beat. `swing: 0.6`
  (0.5 = straight), global and/or per-section.
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

### 4a. Per-voice pan / volume — *quick win, big perceptual payoff*
Emit CC7 (volume) + CC10 (pan) per voice channel (and per section if wanted).
`set_voice_programs` already iterates voices — add the CCs there.
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
