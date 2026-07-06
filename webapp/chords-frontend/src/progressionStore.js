// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// The saved-progression library, stored on-device in localStorage.
//
// It used to live server-side (presets/progressions/*.json via /api/progressions),
// but the container filesystem on Hugging Face Spaces is ephemeral — it resets
// on every rebuild/restart — so saved progressions silently vanished whenever
// the Space redeployed. For a personal, offline-capable PWA instrument the
// library belongs on the device, the way a hardware synth remembers its own
// patches: this survives app restarts and Space redeploys, and works offline.
//
// The functions return Promises so this stays a drop-in replacement for the
// previous fetch-based API (callers already `.then()` them).
const KEY = "chords_library_v1";

function readAll() {
  try {
    const raw = localStorage.getItem(KEY);
    const list = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

function writeAll(list) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list));
  } catch {
    // storage full / unavailable — nothing sensible to do here; the caller's
    // in-memory state stays intact so the user doesn't lose the current edit.
  }
}

export function listProgressions() {
  return Promise.resolve(readAll());
}

export function loadProgression(name) {
  const found = readAll().find((p) => p.name === name);
  return found ? Promise.resolve(found) : Promise.reject(new Error(`Progression '${name}' not found`));
}

export function saveProgression(name, { keys, title = "", tags = [], tempo = null } = {}) {
  const list = readAll();
  const entry = { name, title: title || name, tags, keys, tempo, saved: new Date().toISOString() };
  const i = list.findIndex((p) => p.name === name);
  if (i >= 0) list[i] = entry;
  else list.push(entry);
  writeAll(list);
  return Promise.resolve(entry);
}

export function deleteProgression(name) {
  writeAll(readAll().filter((p) => p.name !== name));
  return Promise.resolve({ ok: true });
}

// Whether a progression already exists under this slug — lets "save as a new
// copy" pick a distinct name instead of clobbering the original.
export function nameExists(name) {
  return readAll().some((p) => p.name === name);
}
