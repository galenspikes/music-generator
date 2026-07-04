// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// Realizes a chord's abstract pitch classes (from /api/parse-keys — see
// generator_api._describe_token's root_pc/pcs/bass_pc fields) into concrete
// MIDI note numbers for an ad-hoc single-chord strike. Deliberately simpler
// than voicing.realize_SATB (which does full 4-voice voice-leading across a
// whole progression) — this is a stateless "just play this chord" rule: place
// the root in a fixed reference octave, then place every other pitch class at
// the nearest position at or above the root (close position), and an optional
// bass note an octave below the root.
//
// Note: `pcs` holds absolute pitch classes (0-11, e.g. G::maj/C -> [2,7,11]
// for D,G,B), not semitone offsets from the root — mtheory.ChordDef.pcs is
// already-resolved chord tones, not the raw CHORD_RECIPES interval list.

const REFERENCE_ROOT_MIDI = 60; // C4

const upFromRoot = (pc, rootPc) => ((pc - rootPc) % 12 + 12) % 12;

export function realizeChord({ root_pc, pcs, bass_pc }) {
  if (root_pc == null || !pcs || pcs.length === 0) return [];
  const rootMidi = REFERENCE_ROOT_MIDI + root_pc;
  const notes = pcs.map((pc) => rootMidi + upFromRoot(pc, root_pc));
  if (bass_pc != null) {
    notes.unshift(rootMidi - 12 + upFromRoot(bass_pc, root_pc));
  }
  return notes;
}
