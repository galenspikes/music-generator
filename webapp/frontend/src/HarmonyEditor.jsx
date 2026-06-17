// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// https://github.com/galenspikes/music-generator
import React, { useEffect, useRef, useState } from "react";

const ROOTS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
const BARE = "(bare)";

/* ---- token <-> structured block (client-side, with a raw fallback) ---- */

function splitTopLevel(s) {
  const out = [];
  let depth = 0, cur = "";
  for (const ch of s) {
    if (ch === "[") { depth++; cur += ch; }
    else if (ch === "]") { depth--; cur += ch; }
    else if (ch === "," && depth === 0) { out.push(cur.trim()); cur = ""; }
    else cur += ch;
  }
  if (cur.trim()) out.push(cur.trim());
  return out;
}

function parseToken(raw) {
  let s = raw.trim();
  if (s.includes("[") || s === "") return { kind: "raw", text: raw };
  let rep = 1;
  const star = s.lastIndexOf("*");
  if (star !== -1) {
    const n = parseInt(s.slice(star + 1), 10);
    if (!isNaN(n)) { rep = n; s = s.slice(0, star); }
  }
  let bass = null;
  const slash = s.indexOf("/");
  if (slash !== -1) { bass = s.slice(slash + 1).trim(); s = s.slice(0, slash); }
  const seg = s.split(":");
  const rootRaw = (seg[0] || "").trim();
  const m = rootRaw.match(/^([A-Ga-g][#b]?)(m|min)?$/);
  if (!m) return { kind: "raw", text: raw };
  const root = m[1][0].toUpperCase() + (m[1][1] || "");
  const inv = (seg[1] || "").trim();
  const recipe = (seg[2] || "").trim();
  return {
    kind: "chord", root,
    recipe: recipe || (m[2] ? "min" : BARE),
    inv: inv === "" ? "" : inv,
    bass: bass || "",
    rep,
  };
}

function serializeToken(b) {
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

const blocksToKeys = (blocks) => blocks.map(serializeToken).join(", ");

const notesTitle = (c) =>
  c.notes && c.notes.length ? `${c.label}: ${c.notes.join(" ")}` : `${c.label} (quality from families)`;

export default function HarmonyEditor({ value, onChange }) {
  const [mode, setMode] = useState("code");
  const [recipes, setRecipes] = useState([]);
  const [parsed, setParsed] = useState({ ok: true, chords: [] });
  const debounce = useRef(null);

  // Draft drives the textarea + chip strip live; the committed `keys` (and
  // thus audio regeneration) only updates on blur, so typing a chord doesn't
  // regenerate on every keystroke.
  const [draft, setDraft] = useState(value || "");
  useEffect(() => { setDraft(value || ""); }, [value]);
  const commitKeys = () => { if (draft !== (value || "")) onChange(draft); };

  useEffect(() => {
    fetch("/api/vocab").then((r) => r.json()).then((d) => setRecipes(d.recipes || [])).catch(() => {});
  }, []);

  // Live parse for the chip strip + inline error (on the uncommitted draft).
  useEffect(() => {
    clearTimeout(debounce.current);
    debounce.current = setTimeout(() => {
      fetch("/api/parse-keys", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ keys: draft || "", mode: "ostinato" }),
      })
        .then((r) => r.json())
        .then(setParsed)
        .catch(() => {});
    }, 250);
    return () => clearTimeout(debounce.current);
  }, [draft]);

  const blocks = mode === "build" ? splitTopLevel(value || "").map(parseToken) : [];
  const setBlocks = (next) => onChange(blocksToKeys(next));
  const editBlock = (i, patch) =>
    setBlocks(blocks.map((b, j) => (j === i ? { ...b, ...patch } : b)));
  const addBlock = () =>
    setBlocks([...blocks, { kind: "chord", root: "C", recipe: "maj7", inv: "", bass: "", rep: 1 }]);

  const segments = parsed.segments || [];
  const rows = Math.min(16, Math.max(3, (draft || "").split("\n").length + 1));

  return (
    <div className="harm">
      <div className="harm-modes">
        <button className={"hm" + (mode === "code" ? " on" : "")} onClick={() => setMode("code")}>code</button>
        <button className={"hm" + (mode === "build" ? " on" : "")} onClick={() => { commitKeys(); setMode("build"); }}>build</button>
      </div>

      {mode === "code" ? (
        <textarea
          className={"harm-text" + (parsed.ok ? "" : " err")}
          rows={rows} spellCheck={false}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commitKeys}
          placeholder={"C::maj7, A::min9, D::min7, G::13\n\nrepeat sections with groups:\n[A, G]*16,  C::maj7, F::maj9, ..."}
        />
      ) : (
        <div className="harm-build">
          {blocks.map((b, i) =>
            b.kind === "raw" ? (
              <div className="cblock raw" key={i}>
                <input value={b.text} spellCheck={false}
                  onChange={(e) => editBlock(i, { text: e.target.value })} />
                <button className="cx" onClick={() => setBlocks(blocks.filter((_, j) => j !== i))}>×</button>
              </div>
            ) : (
              <div className="cblock" key={i}>
                <select value={b.root} onChange={(e) => editBlock(i, { root: e.target.value })}>
                  {ROOTS.map((r) => <option key={r}>{r}</option>)}
                </select>
                <select className="rec" value={b.recipe} onChange={(e) => editBlock(i, { recipe: e.target.value })}>
                  <option value={BARE}>{BARE}</option>
                  {recipes.map((r) => <option key={r}>{r}</option>)}
                </select>
                <input className="inv" placeholder="inv" value={b.inv}
                  onChange={(e) => editBlock(i, { inv: e.target.value.replace(/[^0-9]/g, "") })} />
                <select className="bass" value={b.bass} onChange={(e) => editBlock(i, { bass: e.target.value })}>
                  <option value="">/bass</option>
                  {ROOTS.map((r) => <option key={r}>{r}</option>)}
                </select>
                <input className="rep" type="number" min="1" value={b.rep}
                  onChange={(e) => editBlock(i, { rep: Math.max(1, parseInt(e.target.value, 10) || 1) })} />
                <button className="cx" onClick={() => setBlocks(blocks.filter((_, j) => j !== i))}>×</button>
              </div>
            )
          )}
          <button className="cadd" onClick={addBlock}>+ chord</button>
        </div>
      )}

      {!parsed.ok && (
        <div className="harm-err">⚠ {parsed.error}</div>
      )}

      {parsed.ok && segments.length > 0 && (
        <div className="harm-strip">
          <div className="strip-head">
            <span className="strip-label">plays</span>
            <span className="strip-count">{parsed.total} chord{parsed.total === 1 ? "" : "s"}</span>
          </div>
          <div className="strip-chips">
            {segments.map((s, i) =>
              s.type === "group" ? (
                <span className="cchip group" key={i}
                  title={s.chords.map(notesTitle).join("  ·  ")}>
                  <span className="grp-b">[</span>
                  {s.chords.map((c, j) => <span className="grp-ch" key={j}>{c.label}</span>)}
                  <span className="grp-b">]</span>
                  <b>×{s.reps}</b>
                </span>
              ) : (
                <span className="cchip" key={i} title={notesTitle(s)}>
                  {s.label}{s.reps > 1 && <b>×{s.reps}</b>}
                </span>
              )
            )}
          </div>
        </div>
      )}
    </div>
  );
}
