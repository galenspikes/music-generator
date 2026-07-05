// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// Pure string assembly for the chord token grammar (root[:inversion][:recipe]
// [/bass]*rep, plus [a,b,c]*N groups — docs/reference/token-grammar.md). No
// chord theory here, that stays server-side behind /api/parse-keys. Ported
// from webapp/frontend/src/HarmonyEditor.jsx's parseToken/serializeToken,
// which this app's tap-driven builder replaces with popups/steppers.

export const ROOTS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
export const BARE = "(bare)";

// A stable id per block (not part of the token grammar) so ephemeral,
// per-chord UI state — like the Strike/Sustain/Arpeggio/Loop playback mode —
// survives reordering instead of being keyed by array index.
let nextId = 1;
export const makeId = () => nextId++;

export function splitTopLevel(s) {
  const out = [];
  let depth = 0,
    cur = "";
  for (const ch of s) {
    if (ch === "[") {
      depth++;
      cur += ch;
    } else if (ch === "]") {
      depth--;
      cur += ch;
    } else if (ch === "," && depth === 0) {
      out.push(cur.trim());
      cur = "";
    } else cur += ch;
  }
  if (cur.trim()) out.push(cur.trim());
  return out;
}

function parseChordToken(raw) {
  let s = raw.trim();
  let rep = 1;
  const star = s.lastIndexOf("*");
  if (star !== -1) {
    const n = parseInt(s.slice(star + 1), 10);
    if (!isNaN(n)) {
      rep = n;
      s = s.slice(0, star);
    }
  }
  let bass = null;
  const slash = s.indexOf("/");
  if (slash !== -1) {
    bass = s.slice(slash + 1).trim();
    s = s.slice(0, slash);
  }
  const seg = s.split(":");
  const rootRaw = (seg[0] || "").trim();
  const m = rootRaw.match(/^([A-Ga-g][#b]?)(m|min)?$/);
  if (!m) return { kind: "raw", text: raw, id: makeId() };
  const root = m[1][0].toUpperCase() + (m[1][1] || "");
  const inv = (seg[1] || "").trim();
  const recipe = (seg[2] || "").trim();
  return {
    kind: "chord",
    id: makeId(),
    root,
    recipe: recipe || (m[2] ? "min" : BARE),
    inv: inv === "" ? "" : inv,
    bass: bass || "",
    rep,
  };
}

// A top-level token is either a whole `[...]*N` group or a plain chord token
// — splitTopLevel already isolates these, so "starts with [" reliably means
// "this whole token is a group". Groups don't nest (matches the grammar/
// server-side _segment_keys, which only unwraps one bracket level).
export function parseToken(raw) {
  const s = raw.trim();
  if (s === "") return { kind: "raw", text: raw, id: makeId() };
  if (s.startsWith("[")) {
    const closeIdx = s.lastIndexOf("]");
    if (closeIdx === -1) return { kind: "raw", text: raw, id: makeId() };
    const inner = s.slice(1, closeIdx);
    const rest = s.slice(closeIdx + 1).trim();
    let rep = 1;
    if (rest !== "") {
      const m = rest.match(/^\*(\d+)$/);
      if (!m) return { kind: "raw", text: raw, id: makeId() };
      rep = parseInt(m[1], 10);
    }
    const chords = inner
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean)
      .map(parseChordToken);
    if (chords.length === 0) return { kind: "raw", text: raw, id: makeId() };
    return { kind: "group", id: makeId(), rep, chords };
  }
  return parseChordToken(s);
}

export function serializeToken(b) {
  if (b.kind === "raw") return b.text;
  if (b.kind === "group") {
    const inner = b.chords.map(serializeToken).join(", ");
    return b.rep && b.rep > 1 ? `[${inner}]*${b.rep}` : `[${inner}]`;
  }
  const hasRecipe = b.recipe && b.recipe !== BARE;
  let s;
  if (b.inv !== "" && b.inv != null) s = `${b.root}:${b.inv}:${hasRecipe ? b.recipe : ""}`;
  else if (hasRecipe) s = `${b.root}::${b.recipe}`;
  else s = b.root;
  if (b.bass) s += `/${b.bass}`;
  if (b.rep && b.rep > 1) s += `*${b.rep}`;
  return s;
}

export const blocksToKeys = (blocks) => blocks.map(serializeToken).join(", ");

export function defaultChordBlock() {
  return { kind: "chord", id: makeId(), root: "C", recipe: "maj7", inv: "", bass: "", rep: 1 };
}

export function defaultGroupBlock() {
  return { kind: "group", id: makeId(), rep: 2, chords: [defaultChordBlock(), defaultChordBlock()] };
}
