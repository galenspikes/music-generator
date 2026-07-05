// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// Turns /api/parse-keys' `segments` (top-level chords + groups, the same
// compact structure the chip strip renders) into human-readable labels —
// shared by the Library's mini-preview chips and the Save dialog's
// auto-suggested title.

export function labelForSegment(s) {
  const reps = s.reps > 1 ? `×${s.reps}` : "";
  return s.type === "group" ? `[${s.chords.map((c) => c.label).join(" ")}]${reps}` : `${s.label}${reps}`;
}

export function segmentLabels(segments) {
  return (segments || []).map(labelForSegment);
}

// A short "C - Am - F - G" style summary for defaulting a save-dialog title —
// capped so a long progression doesn't produce an unwieldy name.
export function summarizeSegments(segments, maxSegments = 4) {
  if (!segments || segments.length === 0) return "";
  const shown = segments.slice(0, maxSegments).map(labelForSegment);
  const suffix = segments.length > maxSegments ? "…" : "";
  return shown.join(" - ") + suffix;
}
