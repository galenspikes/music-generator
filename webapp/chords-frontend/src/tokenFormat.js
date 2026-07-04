// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// Pure string assembly for the `root[:inversion][:recipe][/bass]*rep` chord
// token grammar (docs/reference/token-grammar.md) — no chord theory here,
// that stays server-side behind /api/parse-keys. Ported from
// webapp/frontend/src/HarmonyEditor.jsx's parseToken/serializeToken, which
// this app's tap-driven builder replaces with popups/steppers.

export const ROOTS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
export const BARE = "(bare)";

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

export function parseToken(raw) {
  let s = raw.trim();
  if (s.includes("[") || s === "") return { kind: "raw", text: raw };
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
  if (!m) return { kind: "raw", text: raw };
  const root = m[1][0].toUpperCase() + (m[1][1] || "");
  const inv = (seg[1] || "").trim();
  const recipe = (seg[2] || "").trim();
  return {
    kind: "chord",
    root,
    recipe: recipe || (m[2] ? "min" : BARE),
    inv: inv === "" ? "" : inv,
    bass: bass || "",
    rep,
  };
}

export function serializeToken(b) {
  if (b.kind === "raw") return b.text;
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
  return { kind: "chord", root: "C", recipe: "maj7", inv: "", bass: "", rep: 1 };
}
