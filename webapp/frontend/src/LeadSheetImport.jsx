// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// https://github.com/galenspikes/music-generator
//
// Upload a lead-sheet PDF, review/edit the extracted chart, then load it into
// the player as a song. Talks to POST /api/leadsheet/extract (PDF -> chart +
// warnings) and POST /api/leadsheet/emit (chart + transpose -> song.yml),
// re-emitting on every edit so "Load into player" always sends the current
// song.yml. Nothing is written to disk on either end.
import React, { useEffect, useRef, useState } from "react";
import { TextField, IntField } from "./controls.jsx";

const measuresToText = (measures) =>
  (measures || []).map((m) => (m || []).join(" ")).join(" | ");

const textToMeasures = (text) =>
  text.split("|").map((seg) => seg.trim().split(/\s+/).filter(Boolean)).filter((m) => m.length);

export default function LeadSheetImport({ onLoad }) {
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [chart, setChart] = useState(null);
  const [warnings, setWarnings] = useState([]);
  const [transpose, setTranspose] = useState(0);
  const [songYaml, setSongYaml] = useState("");
  const [emitError, setEmitError] = useState("");
  const fileRef = useRef(null);

  const reset = () => {
    setChart(null); setWarnings([]); setError("");
    setTranspose(0); setSongYaml(""); setEmitError("");
  };

  async function handleFile(file) {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch("/api/leadsheet/extract", { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setChart(data.chart);
      setWarnings(data.warnings || []);
      setSongYaml(data.song_yaml || "");
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  // Re-emit song.yml whenever the reviewed chart or transpose changes.
  useEffect(() => {
    if (!chart) return;
    let cancelled = false;
    fetch("/api/leadsheet/emit", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ chart, transpose }),
    })
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (cancelled) return;
        if (!res.ok) { setEmitError(data.detail || `HTTP ${res.status}`); setSongYaml(""); return; }
        setEmitError("");
        setSongYaml(data.song_yaml || "");
      })
      .catch((e) => { if (!cancelled) setEmitError(String(e.message || e)); });
    return () => { cancelled = true; };
  }, [chart, transpose]);

  const setTitle = (title) => setChart((c) => ({ ...c, title }));
  const setTempo = (tempo) => setChart((c) => ({ ...c, tempo }));
  const setSectionName = (idx, name) =>
    setChart((c) => {
      const sections = [...c.sections];
      sections[idx] = { ...sections[idx], name };
      return { ...c, sections };
    });
  const setSectionMeasures = (idx, text) =>
    setChart((c) => {
      const sections = [...c.sections];
      sections[idx] = { ...sections[idx], measures: textToMeasures(text) };
      return { ...c, sections };
    });
  const addSection = () =>
    setChart((c) => ({
      ...c,
      sections: [...(c.sections || []), { name: `section${(c.sections || []).length + 1}`, measures: [] }],
    }));
  const removeSection = (idx) =>
    setChart((c) => ({ ...c, sections: c.sections.filter((_, i) => i !== idx) }));

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files?.[0]);
  };

  return (
    <div className="import-widget">
      <div
        className={"import-dropzone" + (dragging ? " drag" : "")}
        onClick={() => fileRef.current && fileRef.current.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <input
          ref={fileRef} type="file" accept="application/pdf" hidden
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
        {busy ? "extracting…" : "⇪ drop a lead-sheet PDF here, or click to choose one"}
      </div>
      {error && <div className="import-error">{error}</div>}

      {chart && (
        <div className="modal-overlay" onClick={reset}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h3>Review extracted chart</h3>

            {warnings.length > 0 && (
              <ul className="import-warnings">
                {warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            )}

            <div className="modal-field import-meta">
              <div>
                <label>Title:</label>
                <TextField value={chart.title} mono={false} onChange={setTitle} />
              </div>
              <div>
                <label>Tempo:</label>
                <IntField value={chart.tempo} min={20} max={300} onChange={setTempo} />
              </div>
              <div>
                <label>Transpose (semitones):</label>
                <IntField value={transpose} min={-12} max={12} onChange={setTranspose} />
              </div>
            </div>

            <div className="import-sections">
              {(chart.sections || []).map((s, i) => (
                <div className="import-section" key={i}>
                  <div className="import-section-head">
                    <TextField value={s.name} mono={false} onChange={(v) => setSectionName(i, v)} />
                    <button className="import-section-remove" title="remove section"
                      onClick={() => removeSection(i)}>×</button>
                  </div>
                  <TextField
                    value={measuresToText(s.measures)}
                    onChange={(v) => setSectionMeasures(i, v)}
                    multiline
                    placeholder="Cm7 F7 | Bbmaj7 Ebmaj7"
                  />
                </div>
              ))}
              <button className="import-add-section" onClick={addSection}>+ section</button>
            </div>

            {emitError && <div className="import-error">{emitError}</div>}

            <div className="modal-actions">
              <button onClick={reset}>Cancel</button>
              <button
                disabled={!songYaml || !!emitError}
                onClick={() => { onLoad(songYaml, chart.title); reset(); }}
              >
                Load into player
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
