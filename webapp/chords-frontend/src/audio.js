// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// Client-side soundfont playback via smplr (https://github.com/danigb/smplr) —
// pure Web Audio, no Tone.js/@magenta dependency, so a single chord can be
// struck instantly with no backend round-trip. The AudioContext + instrument
// are created lazily on first user gesture (iOS/Chrome autoplay policy),
// mirroring site/_chords.js's ensureAudio() pattern.
import { Soundfont } from "smplr";

export const INSTRUMENTS = [
  { id: "acoustic_grand_piano", label: "Grand Piano" },
  { id: "electric_piano_1", label: "Electric Piano" },
];

let ctx = null;
let instrument = null;
let currentInstrumentId = null;
let activeStops = [];
let progressionTimers = [];

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

// Stop only the currently-ringing notes (used between progression steps —
// does NOT cancel already-scheduled future steps).
function stopNotes() {
  for (const stop of activeStops) stop();
  activeStops = [];
}

// Full stop: cancels any scheduled progression steps too. Call this whenever
// the user starts a new, independent playback action.
export function stopAll() {
  for (const timer of progressionTimers) clearTimeout(timer);
  progressionTimers = [];
  stopNotes();
}

async function strike(midiNotes, instrumentId, velocity) {
  const inst = await ensureInstrument(instrumentId);
  stopNotes();
  activeStops = (midiNotes || []).map((note) => inst.start({ note, velocity }));
}

export async function playChord(midiNotes, { instrumentId = INSTRUMENTS[0].id, velocity = 92 } = {}) {
  if (!midiNotes || midiNotes.length === 0) return;
  stopAll(); // a one-off chord tap also cancels any running progression
  await strike(midiNotes, instrumentId, velocity);
}

// chords: [{ notes: number[] }], each held until the next one starts.
export async function playProgression(chords, { instrumentId = INSTRUMENTS[0].id, bpm = 96 } = {}) {
  stopAll();
  if (!chords || chords.length === 0) return;
  await ensureInstrument(instrumentId);
  const beatMs = (60 / bpm) * 1000 * 2; // two beats per chord strike
  chords.forEach((chord, i) => {
    const timer = setTimeout(() => strike(chord.notes, instrumentId, 92), i * beatMs);
    progressionTimers.push(timer);
  });
}
