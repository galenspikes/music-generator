// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// Client-side soundfont playback via smplr (https://github.com/danigb/smplr) —
// pure Web Audio, no Tone.js/@magenta dependency, so a chord can be struck
// instantly with no backend round-trip. The AudioContext + instrument are
// created lazily on first user gesture (iOS/Chrome autoplay policy).
//
// Playback modes mirror site/_chords.js's transport (Short/Sustain/Arpeggio/
// Loop): Strike is a short, auto-releasing hit; Sustain rings until stopped;
// Arpeggio plays each note in turn once; Loop repeats that arpeggio.
import { Soundfont } from "smplr";

export const INSTRUMENTS = [
  { id: "acoustic_grand_piano", label: "Grand Piano" },
  { id: "electric_piano_1", label: "Electric Piano" },
];

const STRIKE_SECONDS = 1.4; // auto-release length for a short "strike"
const ARPEGGIO_NOTE_SECONDS = 0.9;
const ARPEGGIO_GAP_MS = 150;

let ctx = null;
let instrument = null;
let currentInstrumentId = null;
let activeStops = []; // currently-ringing notes
let stepTimers = []; // scheduled one-shot setTimeouts (progression steps, arpeggio steps)
let loopInterval = null; // setInterval id driving a repeating arpeggio

async function ensureInstrument(instrumentId) {
  if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
  if (ctx.state === "suspended") await ctx.resume();
  if (!instrument || currentInstrumentId !== instrumentId) {
    instrument = Soundfont(ctx, { instrument: instrumentId });
    currentInstrumentId = instrumentId;
    await instrument.ready;
  }
  return instrument;
}

function stopNotes() {
  for (const stop of activeStops) stop();
  activeStops = [];
}

function clearSchedule() {
  for (const t of stepTimers) clearTimeout(t);
  stepTimers = [];
  if (loopInterval) {
    clearInterval(loopInterval);
    loopInterval = null;
  }
}

// Full stop: cancels any scheduled progression/arpeggio/loop steps and any
// currently-ringing notes. Call this whenever the user starts a new,
// independent playback action, or taps Stop.
export function stopAll() {
  clearSchedule();
  stopNotes();
}

async function strikeNotes(midiNotes, instrumentId, velocity, durationSec) {
  const inst = await ensureInstrument(instrumentId);
  stopNotes();
  activeStops = (midiNotes || []).map((note) => inst.start({ note, velocity, duration: durationSec ?? undefined }));
}

// A short, percussive hit — all notes together, auto-releasing.
export async function playChord(midiNotes, { instrumentId = INSTRUMENTS[0].id, velocity = 92 } = {}) {
  if (!midiNotes || midiNotes.length === 0) return;
  stopAll();
  await strikeNotes(midiNotes, instrumentId, velocity, STRIKE_SECONDS);
}

// All notes together, ringing until stopAll() is called.
export async function playSustain(midiNotes, { instrumentId = INSTRUMENTS[0].id, velocity = 92 } = {}) {
  if (!midiNotes || midiNotes.length === 0) return;
  stopAll();
  await strikeNotes(midiNotes, instrumentId, velocity, null);
}

// Notes one at a time, ascending; `loop: true` repeats until stopAll().
export async function playArpeggio(
  midiNotes,
  { instrumentId = INSTRUMENTS[0].id, velocity = 92, loop = false } = {}
) {
  if (!midiNotes || midiNotes.length === 0) return;
  stopAll();
  await ensureInstrument(instrumentId);
  let i = 0;
  const step = () => {
    strikeNotes([midiNotes[i % midiNotes.length]], instrumentId, velocity, ARPEGGIO_NOTE_SECONDS);
    i++;
    if (!loop && i >= midiNotes.length) clearSchedule();
  };
  step();
  loopInterval = setInterval(step, ARPEGGIO_GAP_MS);
}

// chords: [{ notes: number[] }], each held until the next one starts.
// `loop: true` repeats the whole progression until stopAll() is called —
// scheduled as a self-rescheduling pass (not setInterval) since a pass's
// duration depends on chord count/bpm/arpeggiate.
export async function playProgression(
  chords,
  { instrumentId = INSTRUMENTS[0].id, bpm = 96, arpeggiate = false, loop = false } = {}
) {
  stopAll();
  if (!chords || chords.length === 0) return;
  await ensureInstrument(instrumentId);
  const beatMs = (60 / bpm) * 1000 * 2; // two beats per chord
  const passMs = chords.length * beatMs;

  const schedulePass = () => {
    chords.forEach((chord, i) => {
      const at = i * beatMs;
      if (arpeggiate) {
        chord.notes.forEach((note, j) => {
          const t = setTimeout(
            () => strikeNotes([note], instrumentId, 92, Math.min(ARPEGGIO_NOTE_SECONDS, beatMs / 1000)),
            at + j * ARPEGGIO_GAP_MS
          );
          stepTimers.push(t);
        });
      } else {
        const t = setTimeout(() => strikeNotes(chord.notes, instrumentId, 92, (beatMs / 1000) * 0.9), at);
        stepTimers.push(t);
      }
    });
    if (loop) {
      const t = setTimeout(schedulePass, passMs);
      stepTimers.push(t);
    }
  };
  schedulePass();
}
