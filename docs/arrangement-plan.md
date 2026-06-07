# Arrangement layer — design plan (#5)

Status: **Phase 1 shipped.** YAML song files with sections, `repeat`/`bars`
lengths, per-section tempo (tempo map), and per-section instruments/bass/
percussion render end-to-end via `--song` (see `arrangement.py`,
`songs/kiss.yml`, `tests/test_arrangement.py`). Hard cuts between sections;
Phase 2 (transitions/fills, dynamics arc, `seconds:` target) is next.

## Goal
Turn long-form output from a *loop* into a *piece*. Today `--mode ostinato`
repeats one chord chart + one percussion pattern + one instrumentation for the
whole duration; the only evolution is random fills. We want **sections**
(intro / verse / chorus / solo / breakdown / outro) that each have their own
chords, instrumentation, density, and length, sequenced over the timeline.

## What already exists to build on
This is not a from-scratch feature — the engine already thinks in "stages":

- **`build_drum_timeline_stages()`** (+ `PercStage`, `--perc-stages`,
  `--perc-fill-curve`) already walks a list of timed stages, swapping the drum
  pattern per stage and curving the fill rate across the whole timeline. **The
  arrangement layer generalizes this one idea from drums to everything.**
- **Per-voice instruments** (`--voice-instrument`) and **bass styles**
  (`--bass-style`) — the per-section orchestration knobs already exist.
- **`build_chord_timeline()` / `build_arpeggio_events()` / `build_bass_line()`**
  all take a chord sequence + a beats span — they can be called per-section with
  a time offset and concatenated.
- **`MidiOut`** already has per-voice channels; it only needs the ability to
  emit program changes *mid-track* (not just at t=0) so sections can
  re-orchestrate.

## The model

A **Section** is a self-contained render config; a **SongSpec** is global
settings + an ordered list of sections. Each section *overrides* the song-level
defaults (so you only specify what changes).

```yaml
title: Kiss On My List (groove)
tempo: 148
soundfont: SoundFonts/arachno.sf2

defaults:                      # applied to every section unless overridden
  instrument: epiano
  voices: { bass: 33 }
  bass:   { style: octaves, step: 0.5 }
  satb:   arpeggio
  chord_length: h
  perc:   { main: "ebg,eg,ecg,eg, ebg,eg,ecg,eg", fill_rate: 0.18 }
  fx:     lush

sections:
  - name: intro
    repeat: 2
    keys: "G::maj, C::maj, G::maj, Eb::maj, F::maj, C::maj"
    satb: block
    bass: { style: root }
    perc: { fill_rate: 0.0 }            # sparse
  - name: verse
    repeat: 2
    keys: "C::min, F::min7, Ab::maj, Ab::maj/Bb, C::maj, ..."
    bass: { style: root }
  - name: chorus
    repeat: 4
    keys: "G::maj, C::maj, G::maj/C, F::maj/C, ..."
    bass: { style: octaves }
    voices: { soprano: saw }            # bring a lead in
    perc: { fill_rate: 0.30 }           # busier
  - name: solo
    repeat: 2
    keys: "C::maj7, C::maj7, F::maj7, ..."
    instrument: saw
  - name: outro
    repeat: 2
    keys: "G::maj, C::maj, G::maj/C, F::maj/C, ..."
    perc: { fill_rate: 0.05 }
```

Total length = sum of sections (each `repeat` × its chart). A global `seconds:`
could optionally loop/trim the whole arrangement to a target length.

## Engine changes required
1. **`SongSpec` / `Section` dataclasses + loader** (new module
   `arrangement.py`). Merge each section over `defaults`; validate; clear errors.
2. **`MidiOut.program_change_at(voice, program, when_beats)`** — emit a program
   change mid-track at a beat offset so sections re-orchestrate. (Small; it's
   just a timed MIDI message; per-voice channels already exist.)
3. **`arrange(spec) -> events`** orchestrator — for each section:
   build its chord seq → `chord_tl` → harmony + `build_bass_line` events and its
   `drum_tl`, **offset by the section's start beat**, then concatenate. Insert
   program changes at each boundary. This *reuses* the existing builders; the
   flat single-render path becomes the 1-section case.
4. **Continuity across boundaries** — thread `prev_sop` (voice-leading) and the
   bass register cursor from one section into the next for smooth seams.
5. **`--song song.yml`** entry point in `main()` that routes to `arrange()`;
   the existing flat CLI stays untouched (back-compat).

## Phased implementation
- **Phase 1 — sequencing core:** SongSpec/Section + loader; `arrange()` that
  concatenates sections with offsets; `program_change_at`; one MIDI out.
  Per-section: keys, repeat, instrument/voices, bass, satb, perc, chord_length.
  Reference: convert the Kiss chart to `songs/kiss.yml`. Tests for
  loader/merge + section offsetting.
- **Phase 2 — dynamics & polish:** boundary fills/transitions, velocity/
  dynamics arc across the piece, intro/outro fade, `seconds:` target.
- **Phase 3 — stretch:** per-section tempo (needs a tempo map), reusable named
  section "blocks", richer cookbook integration.

## Open decisions (need your call)
1. **File format:** YAML (nicest to hand-edit, adds a `pyyaml` dep) vs JSON
   (no dep, clunkier) vs Python dict (like today's `song_cookbook.py`, max power,
   no parser).
2. **Section length:** `repeat` (loops of the section's chart), `bars`, or
   `seconds` — or support more than one?
3. **v1 tempo:** keep tempo global in v1 (simpler), or per-section from the
   start (tempo map)?
4. **Transitions:** boundary fills in v1, or defer to Phase 2?
