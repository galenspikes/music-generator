// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// https://github.com/galenspikes/music-generator
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Control } from "./controls.jsx";
import HarmonyEditor from "./HarmonyEditor.jsx";
import { PercField, PercList, GrooveSelect, GrooveMulti } from "./PercEditor.jsx";

const GROUP_ORDER = [
  "Engine", "Harmony", "Voicing", "Bass", "Melody",
  "Percussion", "Dynamics", "Process", "Render", "More",
];

// Patchbay-style accent per rack module.
const GROUP_ACCENT = {
  Engine: "#46e0d0", Harmony: "#a98cff", Voicing: "#6aa8ff", Bass: "#ffb454",
  Melody: "#5ad17f", Percussion: "#ff6b9d", Dynamics: "#46c8e0",
  Process: "#ff8a4c", Render: "#9aa4b8", More: "#9aa4b8",
};

const PRESETS = [
  { label: "ii–V–I", keys: "C::maj7, A::min9, D::min7, G::13" },
  { label: "Quartal drift", keys: "D::quartal, E::quartal, G::quartal, A::quartal" },
  { label: "Slash / pedal", keys: "G::maj/C, F::7/Eb, C:1:maj/G, Am::min7" },
  { label: "Chart *N", keys: "[C::maj7, A::min7]*2, G:1:sus2add6*2" },
];

// First-load overrides on top of the schema defaults — a good-sounding start.
const SEED_OVERRIDES = {
  mode: "ostinato",
  keys: "C::maj7, A::min9, D::min7, G::13",
  instrument: "epiano",
  seconds: 16,
  bpm: 120,
  seed: 42,
  chord_len: "q",
  chords_order: "roundrobin",
  bass_style: "root",
  perc_main: "qb, eg, qc, eg",
};

const pretty = (name) => name.replace(/_/g, " ");

export default function App() {
  const [params, setParams] = useState(null);
  const [spec, setSpec] = useState(null);
  const [grooves, setGrooves] = useState([]);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");
  const [tracks, setTracks] = useState([]);
  // On phones, open only Harmony by default — the full rack expanded is an
  // overwhelming scroll. Desktop keeps everything open.
  const [collapsed, setCollapsed] = useState(() => {
    const mobile =
      typeof window !== "undefined" &&
      window.matchMedia &&
      window.matchMedia("(max-width: 640px)").matches;
    if (!mobile) return {};
    return Object.fromEntries(
      GROUP_ORDER.filter((g) => g !== "Harmony").map((g) => [g, true])
    );
  });
  const [downloadUrl, setDownloadUrl] = useState("");

  const [instruments, setInstruments] = useState([]);
  const [songs, setSongs] = useState([]);
  const [currentSong, setCurrentSong] = useState(null);
  const [presets, setPresets] = useState([]);
  const [showLibrary, setShowLibrary] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveTitle, setSaveTitle] = useState("");
  const [saveDesc, setSaveDesc] = useState("");

  const playerRef = useRef(null);
  const vizRef = useRef(null);
  const debounceRef = useRef(null);
  const reqIdRef = useRef(0);

  // Load schema, vocab, songs, presets on mount.
  useEffect(() => {
    Promise.all([
      fetch("/api/schema").then((r) => r.json()),
      fetch("/api/vocab").then((r) => r.json()).catch(() => ({})),
      fetch("/api/songs").then((r) => r.json()).catch(() => ({ songs: [] })),
      fetch("/api/presets").then((r) => r.json()).catch(() => ({ presets: [] })),
    ])
      .then(([schema, vocab, songsData, presetsData]) => {
        setParams(schema.params);
        setGrooves(vocab.grooves || []);
        setInstruments(vocab.instruments || []);
        setSongs(songsData.songs || []);
        setPresets(presetsData.presets || []);

        const base = {};
        for (const p of schema.params) base[p.name] = p.default;
        const overrides = { ...SEED_OVERRIDES };
        if (vocab.perc_lib) overrides.perc_lib = vocab.perc_lib;
        setSpec({ ...base, ...overrides });
        setStatus("idle");

        // Auto-load "kiss" song as the opening demo
        loadSong("kiss");
      })
      .catch((e) => { setError(String(e)); setStatus("error"); });
  }, []);

  // Load a song by name
  const loadSong = (name) => {
    fetch(`/api/songs/${name}`)
      .then((r) => r.json())
      .then((data) => {
        setCurrentSong(name);
        // Merge song spec with current base params
        setSpec((s) => {
          if (!s) return s;
          return { ...s, ...data.spec };
        });
      })
      .catch((e) => console.log("Song load failed:", e.message));
  };

  // Load a preset by name
  const loadPreset = (name) => {
    fetch(`/api/presets/${name}`)
      .then((r) => r.json())
      .then((data) => {
        setCurrentSong(null);
        setSpec((s) => ({ ...s, ...data.spec }));
      })
      .catch((e) => console.log("Preset load failed:", e.message));
  };

  // Save current spec as a preset
  const handleSavePreset = async (presetName) => {
    if (!spec) return;
    try {
      const res = await fetch(`/api/presets/${presetName}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          spec,
          title: saveTitle || presetName,
          description: saveDesc,
        }),
      });
      if (res.ok) {
        // Refresh presets list
        fetch("/api/presets")
          .then((r) => r.json())
          .then((data) => setPresets(data.presets || []))
          .catch(() => {});
        setShowSaveDialog(false);
        setSaveTitle("");
        setSaveDesc("");
      }
    } catch (e) {
      console.log("Save failed:", e.message);
    }
  };

  const setField = (name) => (value) =>
    setSpec((s) => ({ ...s, [name]: value }));

  async function generate(curSpec) {
    const body = curSpec || spec;
    if (!body) return;
    const myId = ++reqIdRef.current;
    setStatus("generating");
    setError("");
    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ spec: body }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      if (myId !== reqIdRef.current) return;
      const bytes = Uint8Array.from(atob(data.midi), (c) => c.charCodeAt(0));
      const url = URL.createObjectURL(new Blob([bytes], { type: "audio/midi" }));
      if (playerRef.current) { try { playerRef.current.stop(); } catch (_) {} playerRef.current.src = url; }
      if (vizRef.current) vizRef.current.src = url;
      setDownloadUrl((old) => { if (old) URL.revokeObjectURL(old); return url; });
      setTracks(data.tracks || []);
      setStatus("ready");
    } catch (err) {
      if (myId === reqIdRef.current) { setError(String(err.message || err)); setStatus("error"); }
    }
  }

  // Unlock Web Audio on the first user gesture. Browsers (and especially
  // cross-origin iframes like the Hugging Face Space embed) start the shared
  // AudioContext suspended; without an explicit resume the midi-player reports
  // "playing" while the audio clock never advances — i.e. play does nothing.
  useEffect(() => {
    const unlock = async () => {
      try {
        if (window.Tone) {
          if (window.Tone.start) await window.Tone.start();
          const ctx = window.Tone.getContext ? window.Tone.getContext().rawContext
                                             : window.Tone.context;
          if (ctx && ctx.state === "suspended" && ctx.resume) await ctx.resume();
        }
      } catch (_) { /* best-effort */ }
    };
    const opts = { capture: true };
    window.addEventListener("pointerdown", unlock, opts);
    window.addEventListener("keydown", unlock, opts);
    return () => {
      window.removeEventListener("pointerdown", unlock, opts);
      window.removeEventListener("keydown", unlock, opts);
    };
  }, []);

  // Always live: debounce-regenerate on any spec change. Text/token fields
  // commit on blur (not per keystroke), so this won't fire mid-chord.
  useEffect(() => {
    if (!spec) return;
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => generate(spec), 320);
    return () => clearTimeout(debounceRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spec]);

  const grouped = useMemo(() => {
    if (!params) return [];
    const by = {};
    for (const p of params) (by[p.group] ||= []).push(p);
    return GROUP_ORDER.filter((g) => by[g]).map((g) => [g, by[g]]);
  }, [params]);

  if (!spec || !params) {
    return <div className="boot">{error ? `error: ${error}` : "booting the rack…"}</div>;
  }

  return (
    <div className="rack">
      <header className="topbar">
        <div className="brand">
          <span className="logo">◇</span>
          <div>
            <h1>MUSIC&nbsp;GENERATOR</h1>
            <p>a token-DSL music box · every knob exposed</p>
            <p className="byline">
              by <a href="https://github.com/galenspikes">Galen Spikes</a>
            </p>
          </div>
        </div>
        <div className="transport">
          <button className="run" title="reroll the seed for a fresh variation"
            onClick={() => setField("seed")(Math.floor(Math.random() * 999999))}>
            ⚄ new take
          </button>
          <span className={`lamp lamp-${status}`} />
          <span className="statustext">{status}</span>
        </div>
      </header>

      {error && <pre className="errbar">{error}</pre>}

      <div className="songbar">
        <button className="btn-library" onClick={() => setShowLibrary(true)}>◈ Library</button>
        {currentSong && (
          <span className="song-current">
            {songs.find((s) => s.name === currentSong)?.title || currentSong}
          </span>
        )}
        <div className="song-actions">
          <button className="btn-new" onClick={() => {
            const base = {};
            for (const p of params) base[p.name] = p.default;
            setSpec({ ...base, ...SEED_OVERRIDES });
            setCurrentSong(null);
          }}>+ New</button>
          <button className="btn-save" onClick={() => setShowSaveDialog(true)}>Save</button>
        </div>
      </div>

      <section className="deck">
        <div className="player-wrap">
          <midi-player
            ref={playerRef}
            sound-font="https://storage.googleapis.com/magentadata/js/soundfonts/sgm_plus"
            visualizer="#viz"
          />
          <midi-visualizer ref={vizRef} id="viz" type="piano-roll" />
          <div className="deck-foot">
            <div className="stems">
              {tracks.map((t) => (
                <span className="stem" key={t.index}>{t.name}<b>{t.notes}</b></span>
              ))}
            </div>
            {downloadUrl && <a className="dl" href={downloadUrl} download="music-generator.mid">⤓ MIDI</a>}
          </div>
        </div>
        <div className="presets">
          {PRESETS.map((p) => (
            <button key={p.label} className="preset" title={p.keys}
              onClick={() => setField("keys")(p.keys)}>{p.label}</button>
          ))}
        </div>
      </section>

      <main className="modules">
        {grouped.map(([group, ps]) => (
          <Panel
            key={group}
            group={group}
            accent={GROUP_ACCENT[group] || "#9aa4b8"}
            collapsed={!!collapsed[group]}
            onToggle={() => setCollapsed((c) => ({ ...c, [group]: !c[group] }))}
          >
            {ps.map((p) => (
              <Param key={p.name} param={p} value={spec[p.name]}
                onChange={setField(p.name)} grooves={grooves} instruments={instruments} />
            ))}
          </Panel>
        ))}
      </main>

      {showLibrary && (
        <div className="lib-overlay" onClick={() => setShowLibrary(false)}>
          <div className="lib-modal" onClick={(e) => e.stopPropagation()}>
            <div className="lib-header">
              <span className="lib-title">Library</span>
              <button className="lib-close" onClick={() => setShowLibrary(false)}>✕</button>
            </div>
            <div className="lib-section">
              <div className="lib-section-label">Songs</div>
              <div className="lib-grid">
                {songs.map((s) => (
                  <div key={s.name} className={"lib-card" + (currentSong === s.name ? " active" : "")}
                    onClick={() => { loadSong(s.name); setShowLibrary(false); }}>
                    <div className="lib-card-title">{s.title}</div>
                    {s.description && <div className="lib-card-desc">{s.description}</div>}
                  </div>
                ))}
              </div>
            </div>
            {presets.length > 0 && (
              <div className="lib-section">
                <div className="lib-section-label">My Presets</div>
                <div className="lib-grid">
                  {presets.map((p) => (
                    <div key={p.name} className="lib-card"
                      onClick={() => { loadPreset(p.name); setShowLibrary(false); }}>
                      <div className="lib-card-title">{p.title || p.name}</div>
                      {p.description && <div className="lib-card-desc">{p.description}</div>}
                      {p.saved && <div className="lib-card-meta">{p.saved.slice(0, 10)}</div>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {showSaveDialog && (
        <div className="modal-overlay" onClick={() => setShowSaveDialog(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Save as Preset</h3>
            <div className="modal-field">
              <label>Preset name:</label>
              <input
                type="text"
                placeholder="my-groove"
                value={saveTitle}
                onChange={(e) => setSaveTitle(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && saveTitle) {
                    handleSavePreset(saveTitle);
                  }
                }}
              />
            </div>
            <div className="modal-field">
              <label>Description:</label>
              <textarea
                placeholder="(optional)"
                value={saveDesc}
                onChange={(e) => setSaveDesc(e.target.value)}
                rows={3}
              />
            </div>
            <div className="modal-actions">
              <button onClick={() => setShowSaveDialog(false)}>Cancel</button>
              <button onClick={() => {
                if (saveTitle) handleSavePreset(saveTitle);
              }} disabled={!saveTitle}>Save</button>
            </div>
          </div>
        </div>
      )}

      <footer className="footer">
        <div className="credit">
          Music Generator — © 2026 <strong>Galen Spikes</strong> · MIT licensed ·{" "}
          <a href="https://github.com/galenspikes/music-generator">source</a>
        </div>
        <div className="credit-sub">
          in-process seam · {params.length} parameters · browser-MIDI preview
        </div>
      </footer>
    </div>
  );
}

function Panel({ group, accent, collapsed, onToggle, children }) {
  return (
    <section className="panel" style={{ "--accent": accent }}>
      <div className="panel-head" onClick={onToggle}>
        <span className="panel-led" />
        <span className="panel-name">{group}</span>
        <span className="panel-chevron">{collapsed ? "▸" : "▾"}</span>
      </div>
      {!collapsed && <div className="panel-body">{children}</div>}
    </section>
  );
}

const SPECIAL = {
  keys: (v, oc) => <HarmonyEditor value={v} onChange={oc} />,
  perc_main: (v, oc) => <PercField value={v} kind="drums" onChange={oc} />,
  perc_interrupters: (v, oc) => <PercList value={v} kind="drums" onChange={oc} />,
  chord_interrupters: (v, oc) => <PercList value={v} kind="chord" onChange={oc} />,
};

function InstrumentPicker({ value, instruments, onChange }) {
  return (
    <div className="param-control" style={{ width: "100%" }}>
      <input
        className="textfield mono" list="instrument-list"
        value={value ?? ""} spellCheck={false}
        placeholder="epiano, strings, 0–127…"
        onChange={(e) => onChange(e.target.value)}
        style={{ width: "100%" }}
      />
      <datalist id="instrument-list">
        {instruments.map((name) => <option key={name} value={name} />)}
      </datalist>
    </div>
  );
}

function Param({ param, value, onChange, grooves, instruments }) {
  // Preset-groove pickers (perc_main_key / perc_intr_keys) — discoverable
  // dropdowns/chips instead of blank text fields.
  if (param.name === "perc_main_key") {
    return (
      <div className="param">
        <div className="param-label">
          <span>{pretty(param.name)}</span>
          {param.help && <span className="info" data-tip={param.help} tabIndex={0} role="button" aria-label={param.help}>?</span>}
        </div>
        <div className="param-control">
          <GrooveSelect value={value} grooves={grooves} onChange={onChange} />
        </div>
      </div>
    );
  }
  if (param.name === "perc_intr_keys") {
    return (
      <div className="param wide">
        <div className="param-label">
          <span>{pretty(param.name)}</span>
          {param.help && <span className="info" data-tip={param.help} tabIndex={0} role="button" aria-label={param.help}>?</span>}
        </div>
        <GrooveMulti value={value} grooves={grooves} onChange={onChange} />
      </div>
    );
  }
  if (param.name === "instrument") {
    return (
      <div className="param wide">
        <div className="param-label">
          <span>{pretty(param.name)}</span>
          {param.help && <span className="info" data-tip={param.help} tabIndex={0} role="button" aria-label={param.help}>?</span>}
        </div>
        <InstrumentPicker value={value} instruments={instruments} onChange={onChange} />
      </div>
    );
  }

  const special = SPECIAL[param.name];
  if (special) {
    return (
      <div className="param wide">
        <div className="param-label">
          <span>{pretty(param.name)}</span>
          {param.help && <span className="info" data-tip={param.help} tabIndex={0} role="button" aria-label={param.help}>?</span>}
        </div>
        {special(value, onChange)}
      </div>
    );
  }
  const wide = ["text", "taglist", "chips"].includes(param.control) || param.multiline;
  return (
    <div className={"param" + (wide ? " wide" : "")}>
      <div className="param-label">
        <span>{pretty(param.name)}</span>
        {param.help && <span className="info" data-tip={param.help} tabIndex={0} role="button" aria-label={param.help}>?</span>}
      </div>
      <div className="param-control">
        <Control param={param} value={value} onChange={onChange} />
      </div>
    </div>
  );
}
