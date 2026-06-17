# Webapp UI/UX Design Plan

## Vision
**Instrument-like, tactile, analog interface.** A blank canvas that invites play—professional, powerful, and fun (inspired by U-He Bazille, DM-1 drum machine, modular synths). For musicians, producers, composers of all levels: from kids to Trent Reznor.

**Opening moment:** Hit play and hear a killer groove (Kiss On My List, full-length). Immediate gratification before deep exploration.

---

## Core Decisions

### Layout & Navigation
```
┌────────────────────────────────────────┐
│  TRANSPORT BAR                         │  Top: tempo, master vol, seed, PLAY
│  (BPM | Master Vol | Seed | ▶ PLAY)   │
├────────────────────────────────────────┤
│                                        │
│  [SIMPLE VIEW] [+ DETAILS toggle]     │
│                                        │
│  Harmony Panel                         │  Main editing canvas
│  Drums Panel                           │
│  Voicing (SATB/Dense)                  │
│  [+ Advanced Rack if Details ON]       │
│                                        │
├────────────────────────────────────────┤
│  PLAYER                                │  Bottom: visual feedback
│  Piano roll + waveform + track info   │
│  [Master | Stems]                      │
└────────────────────────────────────────┘
```

### View Modes
- **Simple** (default): Harmony, Drums, Voicing, Transport. "The main thing."
- **+ Details**: Reveal full modular rack (all 51 params). Grouped panels with accent colors.

Toggle in top-right corner.

### Transport Bar (Always Visible)
- **BPM**: Knob + numeric display. Snap to common tempos (60, 90, 120, 140, 160…).
- **Master Volume**: Vertical slider, 0–100%, visual dB readout.
- **Seed**: Text field (auto-randomizes, or set manual seed for reproducibility).
- **PLAY button**: Large, tactile, visual press-feedback. Spacebar shortcut.
- **Status**: "Playing…" / "Ready" indicator.

---

## Opening Demo: "Kiss On My List" (Hall & Oates)

### Pre-loaded Behavior
1. On first load: auto-load "Kiss On My List" (20-min version, 148 BPM).
2. Display: "Kiss On My List (Hall & Oates) — Press PLAY or hit SPACE"
3. User hits PLAY → full groove streams, piano-roll visualizes in real-time.
4. While playing, they can *edit the harmony or drums mid-stream* → live regeneration.

### Implementation
- Pre-render a 20-min MIDI file (`songs/kiss.yml → midi/kiss_opening_demo.mid`).
- Store as part of `webapp/frontend/public/` (versioned, not too large for embed).
- Backend: `/api/preset/kiss` endpoint returns the MIDI bytes + metadata (title, bpm, duration).
- Frontend: on load, fetch and display. User can edit or hit play immediately.

**Benefits:**
- Zero latency on first interaction (MIDI is already there).
- Demonstrates the full song structure, vocies, drums—everything you can edit.
- Inviting: "you just made this" (because you can edit it live).

---

## Tactile & Visual Details

### Knobs & Sliders
- **Knob**: SVG rotary, drag-to-turn or scroll-to-adjust. Realistic shadows/reflection. Accent color per panel.
- **Slider**: Thick, vertical or horizontal. Snap points for common values.
- **Buttons**: Visual press (tiny inset shadow), release (raised). LED toggles (lit/unlit state).
- **Text fields**: Monospace font, subtle border. Visual feedback on focus.

### Color & Aesthetic
- **Dark theme**: Deep charcoal/black background (like hardware in a studio).
- **Accent colors per panel**: 
  - Harmony → amber/gold
  - Drums → red/rust
  - Voicing → blue
  - Bass → green
  - Render → purple
- **Minimal chrome**: No gradients or faux leather. Clean lines, real materials.

### Feedback & Meters
- **Waveform display** (bottom): Shows the MIDI envelope (note-on/off) in real-time as you play.
- **Piano roll**: Renders the track in a miniature (not interactive, just visual).
- **Track meter**: Master level + per-track info (# notes, duration).

---

## Interaction Patterns

### Edit → Play Loop
1. User types in Harmony field or clicks drums in the grid.
2. Frontend debounces (320ms) and calls `/api/generate`.
3. Backend regenerates in-process (~0.16s for 20min).
4. MIDI bytes stream back, frontend decodes, player updates.
5. Piano roll re-renders live.
6. User hits PLAY or it auto-plays (configurable).

### Presets & Save
- **Load**: Dropdown or gallery of `.yml` songs (`songs/kiss.yml`, `songs/four_organs.yml`…).
- **Save**: "My Groove" dialog → download MIDI + JSON snapshot of params.
- **Quick save**: Seed-based (user hits "Save Seed" → shows "Groove #1537").

---

## Phases

### Phase 1: Polish & Opening (This Sprint)
- [ ] Transport bar (BPM, vol, seed, play).
- [ ] Pre-render Kiss opening demo.
- [ ] Wire demo load + auto-play.
- [ ] Simple/Details toggle.
- [ ] Tactile knob visuals (improve from current).
- [ ] Waveform display at bottom.
- **Ship:** A "blank canvas" that auto-plays something beautiful, feels like hardware, invites editing.

### Phase 2: Real Audio & Mixer (Next)
- FluidSynth per-stem rendering (backend).
- Solo/mute per track (stems).
- Master reverb/chorus controls.
- Preset gallery (songs/*.yml).

### Phase 3: UX Refinement (Polish)
- Accessibility (WCAG, keyboard nav, screen reader).
- Performance tuning (large MIDI, faster regen).
- Code autocomplete for harmony/drums.
- Responsive design (mobile? tablet?).

---

## Success Metrics
- **First-time user:** Lands, sees "Kiss On My List", hits play, hears it, feels like an instrument.
- **Musician:** Can tweak harmony/drums, hear changes live, feel responsive.
- **Tinkerer:** Details toggle reveals the full power (all 51 params).
- **Vibe:** Professional, fun, tactile—not sterile, not frivolous.
