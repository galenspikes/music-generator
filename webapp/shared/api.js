// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// Thin fetch wrappers over the FastAPI backend, shared between webapp/frontend
// and webapp/chords-frontend so the chord/token API contract lives in one
// place. No chord-theory logic here — that all stays server-side.

async function asJson(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      // response wasn't JSON; keep statusText
    }
    throw new Error(detail);
  }
  return res.json();
}

export function fetchVocab() {
  return fetch("/api/vocab").then(asJson);
}

export function fetchRecipes() {
  return fetch("/api/recipes").then(asJson).then((d) => d.recipes || []);
}

export function parseKeys(keys, mode = "ostinato") {
  return fetch("/api/parse-keys", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ keys: keys || "", mode }),
  }).then(asJson);
}

export function listProgressions() {
  return fetch("/api/progressions").then(asJson).then((d) => d.progressions || []);
}

export function loadProgression(name) {
  return fetch(`/api/progressions/${encodeURIComponent(name)}`).then(asJson);
}

export function saveProgression(name, { keys, title = "", tags = [], tempo = null, voicing = null }) {
  return fetch(`/api/progressions/${encodeURIComponent(name)}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ keys, title, tags, tempo, voicing }),
  }).then(asJson);
}

export function deleteProgression(name) {
  return fetch(`/api/progressions/${encodeURIComponent(name)}`, { method: "DELETE" }).then(asJson);
}
