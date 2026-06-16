// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// https://github.com/galenspikes/music-generator
import React, { useEffect, useRef, useState } from "react";

/* ---- token helpers (bracket-aware so [vel+1,prob.5] isn't split) ---- */
function splitTokens(s) {
  const out = [];
  let depth = 0, cur = "";
  for (const ch of s || "") {
    if (ch === "[") { depth++; cur += ch; }
    else if (ch === "]") { depth--; cur += ch; }
    else if (ch === "," && depth === 0) { out.push(cur.trim()); cur = ""; }
    else cur += ch;
  }
  if (cur.trim()) out.push(cur.trim());
  return out;
}
const stripMods = (s) => s.replace(/\[[^\]]*\]/g, "");

/* ---- step grid <-> token string ---- */
const SEQ_ROWS = [
  { letter: "b", name: "Kick" },
  { letter: "c", name: "Snare" },
  { letter: "g", name: "Hat" },
  { letter: "i", name: "Open Hat" },
  { letter: "f", name: "Clap" },
  { letter: "k", name: "Ride" },
  { letter: "s", name: "Tom" },
  { letter: "x", name: "Cowbell" },
];

function gridFromValue(value, steps, resolution) {
  const grid = {};
  SEQ_ROWS.forEach((r) => (grid[r.letter] = Array(steps).fill(false)));
  const toks = splitTokens(value);
  let fits = toks.length > 0 && toks.length === steps;
  toks.forEach((tok, i) => {
    if (i >= steps) { fits = false; return; }
    const dur = tok[0]?.toLowerCase();
    if (dur !== resolution) fits = false;
    const letters = stripMods(tok.slice(1)).toLowerCase();
    if (letters === "r" || letters === "") return;
    for (const ch of letters) {
      if (grid[ch]) grid[ch][i] = true;
      else fits = false; // a letter outside the row set; toggling would drop it
    }
  });
  return { grid, fits };
}

function valueFromGrid(grid, steps, resolution) {
  const toks = [];
  for (let i = 0; i < steps; i++) {
    const letters = SEQ_ROWS.filter((r) => grid[r.letter][i]).map((r) => r.letter).join("");
    toks.push(resolution + (letters || "r"));
  }
  return toks.join(", ");
}

function PercSequencer({ value, onChange }) {
  const [steps, setSteps] = useState(16);
  const [resolution, setResolution] = useState("s");
  const { grid, fits } = gridFromValue(value, steps, resolution);

  const write = (g, s = steps, r = resolution) => onChange(valueFromGrid(g, s, r));
  const toggle = (letter, i) =>
    write({ ...grid, [letter]: grid[letter].map((v, j) => (j === i ? !v : v)) });
  const changeSteps = (n) => { setSteps(n); write(gridFromValue(value, n, resolution).grid, n); };
  const changeRes = (r) => { setResolution(r); write(gridFromValue(value, steps, r).grid, steps, r); };
  const clear = () => {
    const g = {}; SEQ_ROWS.forEach((row) => (g[row.letter] = Array(steps).fill(false)));
    write(g);
  };

  return (
    <div className="seq">
      <div className="seq-bar">
        <span className="seq-lbl">steps</span>
        {[8, 16, 32].map((n) => (
          <button key={n} className={"seq-opt" + (steps === n ? " on" : "")} onClick={() => changeSteps(n)}>{n}</button>
        ))}
        <span className="seq-lbl">grid</span>
        {[["e", "8th"], ["s", "16th"], ["t", "32nd"]].map(([r, lbl]) => (
          <button key={r} className={"seq-opt" + (resolution === r ? " on" : "")} onClick={() => changeRes(r)}>{lbl}</button>
        ))}
        <button className="seq-clear" onClick={clear}>clear</button>
      </div>

      {value && !fits && (
        <div className="seq-note">⚠ pattern not a clean {steps}-step grid — editing here normalizes it</div>
      )}

      <div className="seq-grid">
        {SEQ_ROWS.map((row) => (
          <div className="seq-row" key={row.letter}>
            <span className="seq-name" title={row.letter}>{row.name}</span>
            <div className="seq-cells">
              {Array.from({ length: steps }).map((_, i) => (
                <button
                  key={i}
                  className={"seq-cell" + (grid[row.letter][i] ? " on" : "") + (i % 4 === 0 ? " beat" : "")}
                  onClick={() => toggle(row.letter, i)}
                  aria-label={`${row.name} step ${i + 1}`}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* A single percussion / interrupter motif. kind = "drums" | "chord".
   Drums get a code/grid mode toggle (the step sequencer). */
export function PercField({ value, onChange, kind = "drums", placeholder }) {
  const [parsed, setParsed] = useState({ ok: true, tokens: [] });
  const [mode, setMode] = useState("code");
  const debounce = useRef(null);

  useEffect(() => {
    clearTimeout(debounce.current);
    if (!value || !value.trim()) { setParsed({ ok: true, tokens: [] }); return; }
    debounce.current = setTimeout(() => {
      fetch("/api/parse-perc", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ pattern: value, kind }),
      })
        .then((r) => r.json())
        .then(setParsed)
        .catch(() => {});
    }, 220);
    return () => clearTimeout(debounce.current);
  }, [value, kind]);

  return (
    <div className="perc">
      {kind === "drums" && (
        <div className="perc-modes">
          <button className={"hm" + (mode === "code" ? " on" : "")} onClick={() => setMode("code")}>code</button>
          <button className={"hm" + (mode === "grid" ? " on" : "")} onClick={() => setMode("grid")}>grid</button>
        </div>
      )}

      {mode === "grid" && kind === "drums" ? (
        <PercSequencer value={value} onChange={onChange} />
      ) : (
        <input
          className={"perc-text" + (parsed.ok ? "" : " err")}
          spellCheck={false}
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder || (kind === "chord" ? "ec, er, sc, qr" : "qb, eg, qc, eg")}
        />
      )}

      {!parsed.ok && parsed.error && <div className="perc-err">⚠ {parsed.error}</div>}
      {parsed.tokens.length > 0 && (
        <div className="perc-strip">
          {parsed.tokens.map((t, i) =>
            t.ok ? (
              <span className={"pchip" + (t.rest ? " rest" : "")} key={i}>
                <b className="dur">{t.dur}</b>
                {t.rest ? "rest" : t.hits.join(" + ")}
              </span>
            ) : (
              <span className="pchip bad" key={i} title={t.error}>{t.token} ✕</span>
            )
          )}
        </div>
      )}
    </div>
  );
}

const bpmLabel = (b) => (Array.isArray(b) && b.length === 2 ? ` · ${b[0]}–${b[1]} bpm` : "");

/* Pick a preset groove by name (perc_main_key). */
export function GrooveSelect({ value, grooves = [], onChange }) {
  return (
    <select className="dropdown" value={value || ""}
      onChange={(e) => onChange(e.target.value || null)}>
      <option value="">(none — use perc main)</option>
      {grooves.map((g) => (
        <option key={g.name} value={g.name}>{g.name}{bpmLabel(g.bpm)}</option>
      ))}
    </select>
  );
}

/* Multi-select preset grooves to borrow fills from (perc_intr_keys). */
export function GrooveMulti({ value = [], grooves = [], onChange }) {
  const set = new Set(value || []);
  const flip = (n) => {
    const s = new Set(set);
    s.has(n) ? s.delete(n) : s.add(n);
    onChange([...s]);
  };
  return (
    <div className="chips">
      {grooves.map((g) => (
        <button key={g.name} className={"tchip" + (set.has(g.name) ? " on" : "")}
          title={`fills from ${g.name}`} onClick={() => flip(g.name)}>
          {g.name}
        </button>
      ))}
    </div>
  );
}

/* A list of motifs (perc_interrupters / chord_interrupters). */
export function PercList({ value = [], onChange, kind = "drums" }) {
  const list = value || [];
  const update = (i, v) => onChange(list.map((x, j) => (j === i ? v : x)));
  const remove = (i) => onChange(list.filter((_, j) => j !== i));
  const add = () => onChange([...list, ""]);
  return (
    <div className="perclist">
      {list.map((motif, i) => (
        <div className="perc-row" key={i}>
          <span className="perc-idx">{i + 1}</span>
          <div className="perc-row-body">
            <PercField value={motif} kind={kind} onChange={(v) => update(i, v)} />
          </div>
          <button className="cx" onClick={() => remove(i)}>×</button>
        </div>
      ))}
      <button className="cadd" onClick={add}>+ motif</button>
    </div>
  );
}
