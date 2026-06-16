// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// https://github.com/galenspikes/music-generator
import React, { useEffect, useRef, useState } from "react";

/* A single percussion / interrupter motif: text in, "parsed as" chips out,
   with inline per-token errors. `kind` = "drums" | "chord". */
export function PercField({ value, onChange, kind = "drums", placeholder }) {
  const [parsed, setParsed] = useState({ ok: true, tokens: [] });
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
      <input
        className={"perc-text" + (parsed.ok ? "" : " err")}
        spellCheck={false}
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder || (kind === "chord" ? "ec, er, sc, qr" : "qb, eg, qc, eg")}
      />
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
