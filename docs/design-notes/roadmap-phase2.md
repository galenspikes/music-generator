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

### 1e. `seconds:` length target — SHIPPED
`length: {seconds: 1200}` loops the whole (already-expanded) section sequence,
computing each repeat's real-world duration from its own tempo (beats * 60 /
tempo, since per-section tempo means beats→seconds isn't constant across the
song) and accumulating until the target is reached; the final repeat is
trimmed (re-expressed in `bars`) to land exactly on target instead of
overshooting by a whole pass. `arrangement._extend_to_length` does the
looping in `build_spec`, using only each section's beat *count* (via
`key_roots`, which has no randomness) so it doesn't perturb the chord RNG.
See [create-an-arrangement.md](../how-to/create-an-arrangement.md).

**Resolved:** loop-whole-form (not extend-the-last-section) is what shipped —
simpler to reason about and keeps the song's dynamics arc (1d) intact across
repeats.

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
- **Bass locked to kick — SHIPPED:** `bass.lock_kick: true` (arrangement) /
  `--bass-lock-kick` (flat CLI) times the independent bass line's onsets to
  this section's kick-drum hits (`percussion.kick_onsets`) instead of the even
  `bass_step` subdivision — resolved as **a modifier on existing styles**
  (orthogonal to the pitch pattern), not a new `--bass-style`. Falls back to
  the step subdivision per-chord for any slot with no kick in its span (see
  `voicing.build_bass_line`'s `kick_times`), so the bass never goes silent.
- **Ghost notes (drums) — SHIPPED:** `perc.ghost_rate`/`perc.ghost_note`
  (arrangement) / `--perc-ghost-rate`/`--perc-ghost-note` (flat CLI) fill empty
  drum-pattern slots with a low-velocity hit at that probability
  (`percussion.add_ghost_notes`).
- **Better humanization:** accent beat 1, velocity curves, tighter/looser feel
  per section.

### Phasing
- **v1:** swing + laid-back snare + accent-on-1 (contained, immediately audible).
- **v2 — SHIPPED:** bass-locked-to-kick + ghost notes.
- **v3:** per-genre feel presets.

**Open questions:** swing global vs per-section? expose raw timing offsets or
ship genre "feel" presets?

**Effort:** v1 small–medium. **Risk:** low (transforms are localized), but feel
needs ear-tuning.

---

## Thread 4 — Mix & stems (release-quality output)

**Goal:** make renders sit right, and enable finishing in a DAW.

### 4a. Per-voice pan / volume — SHIPPED
CC7 (volume) already goes out per voice channel at init. Song-global pan:
`--pan-spread 0..1` emits CC10 per SATB voice from `VOICE_PAN_POS`
(soprano/bass widest, alto/tenor inside; 0 = mono/centred), set under
`defaults: { pan_spread: ... }`. **Explicit per-section pan/vol — SHIPPED:**
`mix.vol`/`mix.pan` (alongside `mix.reverb`/`mix.chorus` from 4c) send raw
CC7/CC10 per voice or "drums" at a section boundary, e.g.
```yaml
mix: { bass: {vol: 105, pan: 64}, soprano: {pan: 84}, drums: {vol: 110} }
```
reusing the same `"cc"` event dispatch built for 4c. See
[create-an-arrangement.md](../how-to/create-an-arrangement.md).

### 4b. Stems export — *the "actually releasable" feature* — MIDI SHIPPED
Voices are already on separate channels/tracks. `MidiOut.write_stems(base_path)`
writes one standalone MIDI file per voice + drums (`song.mid` ->
`song_soprano.mid`, `song_bass.mid`, ..., `song_drums.mid`) — directly
importable into a DAW. Wired to `--stems` (flat CLI path) and
`arrangement.render(spec, out, stems=True)` (song path). See
[create-an-arrangement.md](../how-to/create-an-arrangement.md).

**WAV bounce — SHIPPED.** `render.py --stems` (forwards `--stems` to the
generator, then finds the sibling stem MIDI files `write_stems` produced via
`find_stem_midis` and bounces each through the same FluidSynth pipeline as
the main WAV) — raw, with no independent `--normalize`/`--boost-db`, since
loudness-matching each stem independently would destroy the relative balance
between them. See [render-audio.md](../how-to/render-audio.md). Channel-mute
rendering (the original doc's other option) is superseded — per-stem MIDI is
simpler and was the doc's own recommendation.

### 4c. Per-section FX via CC — SHIPPED
CC91 (reverb send) / CC93 (chorus send) per channel/section for spatial
dynamics without swapping soundfonts:
```yaml
sections:
  - name: solo
    mix: { soprano: {reverb: 90, chorus: 40}, drums: {reverb: 40} }
```
`mix` keys are voice names or `drums`; values are 0–127 sends. New
`MidiOut.control_change_at`/`drum_control_change_at` (mirroring
`program_change_at`) send the CC at the section's beat offset; `render_events`
dispatches a new `"cc"` event kind to them. See
[create-an-arrangement.md](../how-to/create-an-arrangement.md).

**Resolved:** stems as separate MIDI (not channel-mute), bounced to WAV in
`render.py` (not left as MIDI-only) — both per-stem MIDI and the WAV bounce
shipped, see 4b above. Pan/vol per section also shipped — `mix.vol`/`mix.pan`
join `mix.reverb`/`mix.chorus`, see 4a above.

**Effort:** 4a small, 4b medium (needs render orchestration) — done, 4c small
— done. **Risk:** low.

---

## Cross-cutting enabler — port `play_music` → Python `render.py` — SHIPPED

Threads 4b (stems), 4c (per-section FX), and album batch-rendering all get much
easier in Python than in the shell wrapper (which already cost us 3 bug fixes).
`render.py` does generate → FluidSynth → ffmpeg (with `--stems` bounce support,
above); `play_music` is now a thin back-compat shim over it. Album batch
rendering is still open.

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
1. **Quick wins — DONE:** Thread 4a (pan/volume) + Thread 3 v1 (swing/feel).
2. **Composition — DONE:** Thread 1a–1e (form refs, continuity, transitions,
   dynamics, length target) — songs that hold together over 20 minutes.
3. **Groove — DONE:** Thread 3 v2 (bass-locked-to-kick, ghost notes), Thread 4c
   (per-section mix/FX), Thread 4b (stems, MIDI + WAV bounce), the `render.py`
   port.
4. **The hook (next up):** Thread 2 v1–v2 (melody) — the biggest musical leap,
   and the last major unshipped thread. Has open design questions (see
   Thread 2) worth settling before starting.
5. **Polish (smaller, can thread in anytime):** Thread 3 v3 (genre feel
   presets — depends on Thread 3's remaining open question), pocket/
   micro-timing, album batch rendering.

Groove polish (Thread 3 v2+) threads in throughout.
