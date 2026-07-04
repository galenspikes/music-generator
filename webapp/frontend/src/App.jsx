// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// https://github.com/galenspikes/music-generator
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Control, IntField } from "./controls.jsx";
import HarmonyEditor from "./HarmonyEditor.jsx";
import { PercField, PercList, GrooveSelect, GrooveMulti } from "./PercEditor.jsx";
import Docs from "./Docs.jsx";

const GROUP_ORDER = [
  "Engine", "Harmony", "Voicing", "Bass", "Melody",
  "Percussion", "Dynamics", "Render", "More",
];

// Patchbay-style accent per rack module.
const GROUP_ACCENT = {
  Engine: "#46e0d0", Harmony: "#a98cff", Voicing: "#6aa8ff", Bass: "#ffb454",
  Melody: "#5ad17f", Percussion: "#ff6b9d", Dynamics: "#46c8e0",
  Render: "#9aa4b8", More: "#9aa4b8",
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

// Mirrors generator_api.slugify() — good enough for a client-side preview and
// for URL-encoding; the server has final say on the actual saved filename.
const slugify = (text) => {
  const s = (text || "").trim().toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "-").replace(/-{2,}/g, "-").replace(/^-+|-+$/g, "");
  return s || "untitled";
};

// The reserved preset name the app boots into, if the user has saved one —
// see generator_api.HOME_PRESET_NAME.
const HOME_PRESET = "home";

const matchesFilter = (query, ...fields) => {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return fields.some((f) => (f || "").toLowerCase().includes(q));
};

// Same soundfont for the main player and the instrument-preview player, so a
// preview actually matches what playback sounds like. These are the only two
// publicly-hosted soundfont directories in the browser-playable format
// html-midi-player expects (verified reachable; there is no larger public
// library of these — most .sf2 soundfonts are not usable here without an
// offline conversion step, see docs/design-notes/ui-ux-roadmap.md Thread D).
const SOUND_BANKS = [
  { id: "sgm_plus", label: "General MIDI",
    url: "https://storage.googleapis.com/magentadata/js/soundfonts/sgm_plus" },
  { id: "salamander", label: "Salamander Piano (piano only)",
    url: "https://storage.googleapis.com/magentadata/js/soundfonts/salamander",
    note: "Acoustic grand piano samples only — other instruments will be silent or wrong." },
];
const DEFAULT_SOUND_BANK = SOUND_BANKS[0].id;

export default function App() {
  const [params, setParams] = useState(null);
  const [spec, setSpec] = useState(null);
  const [grooves, setGrooves] = useState([]);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");
  const [tracks, setTracks] = useState([]);
  const [envelope, setEnvelope] = useState([]);
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
  const [instrumentCatalog, setInstrumentCatalog] = useState([]);
  const [previewing, setPreviewing] = useState(false);
  const previewPlayerRef = useRef(null);

  // Sound bank is a playback setting, not part of the musical spec — it
  // doesn't get saved into presets/songs, just remembered locally.
  const [soundBank, setSoundBank] = useState(
    () => (typeof localStorage !== "undefined" && localStorage.getItem("mg_sound_bank")) || DEFAULT_SOUND_BANK
  );
  const [customSoundFont, setCustomSoundFont] = useState(
    () => (typeof localStorage !== "undefined" && localStorage.getItem("mg_custom_soundfont")) || ""
  );
  useEffect(() => {
    if (typeof localStorage !== "undefined") localStorage.setItem("mg_sound_bank", soundBank);
  }, [soundBank]);
  useEffect(() => {
    if (typeof localStorage !== "undefined") localStorage.setItem("mg_custom_soundfont", customSoundFont);
  }, [customSoundFont]);
  const soundFontUrl = soundBank === "custom"
    ? (customSoundFont || SOUND_BANKS[0].url)
    : (SOUND_BANKS.find((b) => b.id === soundBank)?.url || SOUND_BANKS[0].url);
  const [songs, setSongs] = useState([]);
  const [currentSong, setCurrentSong] = useState(null);
  const [presets, setPresets] = useState([]);
  const [tab, setTab] = useState("listen"); // "listen" | "library" | "editor" | "docs"
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveTitle, setSaveTitle] = useState("");
  const [saveDesc, setSaveDesc] = useState("");
  const [saveAsHome, setSaveAsHome] = useState(false);
  const [libraryFilter, setLibraryFilter] = useState("");
  const [activeModule, setActiveModule] = useState("Harmony"); // For mobile module picker

  const playerRef = useRef(null);
  const vizRef = useRef(null);
  const debounceRef = useRef(null);
  const reqIdRef = useRef(0);

  // Switching banks mid-playback would otherwise mix old audio buffers with
  // newly-loaded samples — stop and let the player reload cleanly.
  useEffect(() => {
    try { playerRef.current && playerRef.current.stop(); } catch (_) { /* not ready yet */ }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [soundFontUrl]);

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
        setInstrumentCatalog(vocab.instrument_catalog || []);
        setSongs(songsData.songs || []);
        setPresets(presetsData.presets || []);

        const base = {};
        for (const p of schema.params) base[p.name] = p.default;
        const overrides = { ...SEED_OVERRIDES };
        if (vocab.perc_lib) overrides.perc_lib = vocab.perc_lib;
        setSpec({ ...base, ...overrides });
        setStatus("idle");

        // Boot into the user's home preset if they've set one (ui-homework.md:
        // "the home, or a user-defined home preset") — otherwise the opening demo.
        const hasHome = (presetsData.presets || []).some((p) => p.name === HOME_PRESET);
        if (hasHome) loadPreset(HOME_PRESET);
        else loadSong("kiss");
      })
      .catch((e) => { setError(String(e)); setStatus("error"); });
  }, []);

  const refreshPresets = () =>
    fetch("/api/presets").then((r) => r.json())
      .then((data) => setPresets(data.presets || [])).catch(() => {});

  // Load a song by name
  const loadSong = (name) => {
    fetch(`/api/songs/${encodeURIComponent(name)}`)
      .then((r) => r.json())
      .then((data) => {
        setCurrentSong(name);
        // Merge song spec with current base params
        setSpec((s) => {
          if (!s) return s;
          return { ...s, ...data.spec };
        });
        setTab("listen");
      })
      .catch((e) => console.log("Song load failed:", e.message));
  };

  // Load a preset by name
  const loadPreset = (name) => {
    fetch(`/api/presets/${encodeURIComponent(name)}`)
      .then((r) => r.json())
      .then((data) => {
        setCurrentSong(null);
        setSpec((s) => ({ ...s, ...data.spec }));
        setTab("listen");
      })
      .catch((e) => console.log("Preset load failed:", e.message));
  };

  // Save current spec as a preset. `slug` is what's used in the URL (and thus
  // the filename); `title` is the free-text display name.
  const savePresetAs = async (slug, title, description, spec_) => {
    const res = await fetch(`/api/presets/${encodeURIComponent(slug)}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ spec: spec_, title: title || slug, description }),
    });
    if (!res.ok) throw new Error(`save failed: HTTP ${res.status}`);
  };

  const handleSavePreset = async (title) => {
    if (!spec) return;
    try {
      await savePresetAs(slugify(title), title, saveDesc, spec);
      if (saveAsHome) await savePresetAs(HOME_PRESET, title, saveDesc, spec);
      await refreshPresets();
      setShowSaveDialog(false);
      setSaveTitle("");
      setSaveDesc("");
      setSaveAsHome(false);
    } catch (e) {
      console.log("Save failed:", e.message);
    }
  };

  const handleDeletePreset = async (name, ev) => {
    ev.stopPropagation(); // don't trigger the card's onClick (load)
    if (typeof window !== "undefined" &&
        !window.confirm(`Delete preset "${name}"?`)) return;
    try {
      await fetch(`/api/presets/${encodeURIComponent(name)}`, { method: "DELETE" });
      await refreshPresets();
    } catch (e) {
      console.log("Delete failed:", e.message);
    }
  };

  const handleSetAsHome = async (name, ev) => {
    ev.stopPropagation();
    try {
      const r = await fetch(`/api/presets/${encodeURIComponent(name)}`);
      const data = await r.json();
      const meta = presets.find((p) => p.name === name);
      await savePresetAs(HOME_PRESET, meta?.title || name, meta?.description || "", data.spec);
      await refreshPresets();
    } catch (e) {
      console.log("Set-as-home failed:", e.message);
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
      setEnvelope(data.envelope || []);
      setStatus("ready");
    } catch (err) {
      if (myId === reqIdRef.current) { setError(String(err.message || err)); setStatus("error"); }
    }
  }

  // Play one short, undecorated snippet through the chosen instrument — a
  // literal Cmaj7 vamp (no drums, no bass, frozen voicing) so the timbre is
  // all you hear. Reuses Thread A's --no-perc/--bass-style none/--satb-style
  // static rather than adding a second synthesis path for previews.
  async function previewInstrument(instrumentValue) {
    if (!instrumentValue || previewing) return;
    setPreviewing(true);
    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          spec: {
            mode: "ostinato", keys: "C::maj7", chord_len: "h", seconds: 1.5,
            bpm: 120, seed: 1, no_perc: true, bass_style: "none",
            satb_style: "static", instrument: instrumentValue,
          },
        }),
      });
      if (!res.ok) return;
      const data = await res.json();
      const bytes = Uint8Array.from(atob(data.midi), (c) => c.charCodeAt(0));
      const url = URL.createObjectURL(new Blob([bytes], { type: "audio/midi" }));
      const player = previewPlayerRef.current;
      if (!player) return;
      try { player.stop(); } catch (_) {}
      const onLoad = () => {
        player.removeEventListener("load", onLoad);
        try { player.start(); } catch (_) {}
      };
      player.addEventListener("load", onLoad);
      player.src = url;
    } catch (_) {
      // best-effort preview; a failed preview shouldn't disturb the editor
    } finally {
      setPreviewing(false);
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
        <nav className="topnav">
          <a href="https://galenspikes.github.io/music-generator/" target="_blank" rel="noreferrer">Home</a>
          <a href="https://galenspikes.github.io/music-generator/chords.html" target="_blank" rel="noreferrer">Chords</a>
          <a href="https://github.com/galenspikes/music-generator" target="_blank" rel="noreferrer">GitHub</a>
        </nav>
        <div className="transport">
          <div className="transport-bpm" title="Tempo">
            <span className="transport-bpm-label">BPM</span>
            <IntField value={spec.bpm} min={40} max={300} onChange={setField("bpm")} />
          </div>
          <SoundBankPicker bank={soundBank} onBankChange={setSoundBank}
            customUrl={customSoundFont} onCustomUrlChange={setCustomSoundFont} />
          <button className="run" title="reroll the seed for a fresh variation"
            onClick={() => setField("seed")(Math.floor(Math.random() * 999999))}>
            ⚄ new take
          </button>
          <span className={`lamp lamp-${status}`} />
          <span className="statustext">{status}</span>
        </div>
      </header>

      {error && <pre className="errbar">{error}</pre>}

      <nav className="tabbar">
        <button className={"tab" + (tab === "listen" ? " on" : "")} onClick={() => setTab("listen")}>▸ Listen</button>
        <button className={"tab" + (tab === "library" ? " on" : "")} onClick={() => setTab("library")}>◈ Library</button>
        <button className={"tab" + (tab === "editor" ? " on" : "")} onClick={() => setTab("editor")}>⚙ Editor</button>
        <button className={"tab" + (tab === "docs" ? " on" : "")} onClick={() => setTab("docs")}>❐ Docs</button>
      </nav>

      <div className="songbar">
        <span className="song-current">
          {currentSong ? (songs.find((s) => s.name === currentSong)?.title || currentSong) : "untitled"}
        </span>
        <div className="song-actions">
          <button className="btn-new" onClick={() => {
            const base = {};
            for (const p of params) base[p.name] = p.default;
            setSpec({ ...base, ...SEED_OVERRIDES });
            setCurrentSong(null);
            setTab("editor");
          }}>+ New</button>
          <button className="btn-save" onClick={() => setShowSaveDialog(true)}>Save</button>
        </div>
      </div>

      <section className={"deck" + (tab === "listen" ? "" : " tab-hidden")}>
        <div className="player-wrap">
          <midi-player
            ref={playerRef}
            sound-font={soundFontUrl}
            visualizer="#viz"
          />
          <Waveform envelope={envelope} />
          <midi-visualizer ref={vizRef} id="viz" type="piano-roll" />
          {/* Hidden — plays instrument-preview snippets without disturbing the
              main player's song/state. */}
          <midi-player ref={previewPlayerRef} sound-font={soundFontUrl} style={{ display: "none" }} />
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

      {tab === "library" && (
        <section className="library-page">
          <input
            className="textfield mono lib-filter"
            placeholder="filter songs & presets…"
            value={libraryFilter}
            onChange={(e) => setLibraryFilter(e.target.value)}
          />
          <div className="lib-section">
            <div className="lib-section-label">Songs</div>
            <div className="lib-grid">
              {songs.filter((s) => matchesFilter(libraryFilter, s.title, s.description)).map((s) => (
                <div key={s.name} className={"lib-card" + (currentSong === s.name ? " active" : "")}
                  onClick={() => loadSong(s.name)}>
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
                {presets.filter((p) => matchesFilter(libraryFilter, p.title, p.description))
                  .map((p) => (
                  <div key={p.name} className="lib-card"
                    onClick={() => loadPreset(p.name)}>
                    <div className="lib-card-title">
                      {p.name === HOME_PRESET && <span className="lib-home-badge" title="loads on startup">⌂</span>}
                      {p.title || p.name}
                    </div>
                    {p.description && <div className="lib-card-desc">{p.description}</div>}
                    {p.saved && <div className="lib-card-meta">{p.saved.slice(0, 10)}</div>}
                    <div className="lib-card-actions">
                      {p.name !== HOME_PRESET && (
                        <button className="lib-card-action" title="set as home (loads on startup)"
                          onClick={(ev) => handleSetAsHome(p.name, ev)}>⌂</button>
                      )}
                      <button className="lib-card-action lib-card-delete" title="delete preset"
                        onClick={(ev) => handleDeletePreset(p.name, ev)}>×</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {tab === "editor" && (
        <>
          <main className="modules">
            {grouped.map(([group, ps]) => {
              const isMobile = typeof window !== "undefined" && window.matchMedia && window.matchMedia("(max-width: 640px)").matches;
              if (isMobile && group !== activeModule) return null;
              return (
                <Panel
                  key={group}
                  group={group}
                  accent={GROUP_ACCENT[group] || "#9aa4b8"}
                  collapsed={!!collapsed[group]}
                  onToggle={() => setCollapsed((c) => ({ ...c, [group]: !c[group] }))}
                >
                  {ps.map((p) => (
                    <Param key={p.name} param={p} value={spec[p.name]}
                      onChange={setField(p.name)} grooves={grooves} instruments={instruments}
                      instrumentCatalog={instrumentCatalog}
                      onPreviewInstrument={previewInstrument} previewing={previewing} />
                  ))}
                </Panel>
              );
            })}
          </main>

          {typeof window !== "undefined" && window.matchMedia && window.matchMedia("(max-width: 640px)").matches && (
            <div className="module-picker">
              <div className="module-picker-handle" />
              <div className="module-picker-grid">
                {grouped.map(([group]) => (
                  <button
                    key={group}
                    className={`module-picker-btn ${activeModule === group ? "active" : ""}`}
                    onClick={() => setActiveModule(group)}
                  >
                    {group}
                  </button>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {tab === "docs" && <Docs spec={spec} setField={setField} setTab={setTab} />}

      {showSaveDialog && (
        <div className="modal-overlay" onClick={() => setShowSaveDialog(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Save as Preset</h3>
            <div className="modal-field">
              <label>Preset name:</label>
              <input
                type="text"
                placeholder="My Cool Groove"
                value={saveTitle}
                onChange={(e) => setSaveTitle(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && saveTitle) {
                    handleSavePreset(saveTitle);
                  }
                }}
              />
              {saveTitle && <div className="modal-hint">saves as: {slugify(saveTitle)}</div>}
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
            <label className="modal-checkbox">
              <input type="checkbox" checked={saveAsHome}
                onChange={(e) => setSaveAsHome(e.target.checked)} />
              Also use as my home preset (loads on startup)
            </label>
            <div className="modal-actions">
              <button onClick={() => { setShowSaveDialog(false); setSaveAsHome(false); }}>Cancel</button>
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
          <a href="https://galenspikes.github.io/music-generator/" target="_blank" rel="noreferrer">home</a> ·{" "}
          <a href="https://galenspikes.github.io/music-generator/chords.html" target="_blank" rel="noreferrer">chords</a> ·{" "}
          <a href="https://galenspikes.github.io/music-generator/docs/" target="_blank" rel="noreferrer">docs</a> ·{" "}
          <a href="https://github.com/galenspikes/music-generator" target="_blank" rel="noreferrer">github</a>
        </div>
        <div className="credit-sub">
          in-process seam · {params.length} parameters · browser-MIDI preview
        </div>
      </footer>
    </div>
  );
}

/* Time-bucketed note-density envelope from /api/generate — a lightweight
   "waveform" reading (webapp-ui-design.md), not a precise analytical chart:
   one hue, no legend (single series), no gridlines/tooltip — matches the
   decorative level-meter convention of a real synth/DAW waveform strip. */
function Waveform({ envelope }) {
  if (!envelope || envelope.length === 0) return null;
  return (
    <div className="waveform" role="img" aria-label="note-density envelope over time">
      {envelope.map((v, i) => (
        <div key={i} className="waveform-bar" style={{ height: `${Math.max(4, v * 100)}%` }} />
      ))}
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

/* Which sound bank the browser plays through — a playback setting (not saved
   into presets/songs). Only two public banks exist in the format the player
   can load; a custom-URL field covers anyone hosting their own. */
function SoundBankPicker({ bank, onBankChange, customUrl, onCustomUrlChange }) {
  const current = SOUND_BANKS.find((b) => b.id === bank);
  return (
    <div className="soundbank">
      <select className="dropdown soundbank-select" value={bank}
        onChange={(e) => onBankChange(e.target.value)} title="Sound bank (browser playback)">
        {SOUND_BANKS.map((b) => <option key={b.id} value={b.id}>{b.label}</option>)}
        <option value="custom">Custom URL…</option>
      </select>
      {bank === "custom" && (
        <input
          className="textfield mono soundbank-url"
          placeholder="https://.../soundfont-dir"
          value={customUrl}
          onChange={(e) => onCustomUrlChange(e.target.value)}
        />
      )}
      {current?.note && (
        <span className="info soundbank-note" data-tip={current.note} tabIndex={0}
          role="button" aria-label={current.note}>⚠</span>
      )}
    </div>
  );
}

/* The friendly short aliases (epiano, strings, ...) stay a plain text+datalist
   field — quick to type, and still accepts a raw GM number. "browse" reveals
   the full 128-instrument GM catalog grouped by family, filterable, with a
   preview button per instrument and on the current selection. */
function InstrumentPicker({ value, instruments, catalog = [], onChange,
                           onPreview, previewing }) {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("");

  const groups = React.useMemo(() => {
    const q = filter.trim().toLowerCase();
    const byFamily = new Map();
    for (const entry of catalog) {
      if (q && !entry.name.toLowerCase().includes(q) &&
          !entry.family.toLowerCase().includes(q)) continue;
      if (!byFamily.has(entry.family)) byFamily.set(entry.family, []);
      byFamily.get(entry.family).push(entry);
    }
    return byFamily;
  }, [catalog, filter]);

  const current = String(value ?? "").trim().toLowerCase();

  return (
    <div className="instrument-picker">
      <div className="instrument-row">
        <input
          className="textfield mono" list="instrument-list"
          value={value ?? ""} spellCheck={false}
          placeholder="epiano, strings, 0–127…"
          onChange={(e) => onChange(e.target.value)}
        />
        <button className="preview-btn" title="preview this sound"
          disabled={previewing || !value} onClick={() => onPreview(value)}>
          {previewing ? "…" : "▶"}
        </button>
        <button className={"browse-toggle" + (open ? " on" : "")}
          onClick={() => setOpen((o) => !o)}>
          {open ? "close" : "browse ▾"}
        </button>
      </div>
      <datalist id="instrument-list">
        {instruments.map((name) => <option key={name} value={name} />)}
      </datalist>
      {open && (
        <div className="instrument-browser">
          <input
            className="textfield mono" placeholder="filter by name or family…"
            value={filter} onChange={(e) => setFilter(e.target.value)}
          />
          <div className="instrument-groups">
            {groups.size === 0 && <div className="instrument-empty">no matches</div>}
            {[...groups.entries()].map(([family, entries]) => (
              <div className="instrument-group" key={family}>
                <div className="instrument-group-label">{family}</div>
                <div className="instrument-group-items">
                  {entries.map((e) => (
                    <button
                      key={e.program}
                      className={"ichip" + (current === e.name.toLowerCase() ? " on" : "")}
                      title={`GM ${e.program}`}
                      onClick={() => onChange(e.name)}
                    >
                      <span
                        className="ichip-play"
                        title={`preview ${e.name}`}
                        onClick={(ev) => { ev.stopPropagation(); onPreview(e.name); }}
                      >▶</span>
                      {e.name}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const VOICES = ["soprano", "alto", "tenor", "bass"];

/* Per-voice instrument override (--voice-instrument VOICE=NAME), as four
   compact pickers instead of the generic "type VOICE=NAME, hit enter" taglist. */
function VoiceInstrumentPicker({ value = [], instruments, onChange, onPreview }) {
  const map = {};
  for (const entry of value || []) {
    const s = String(entry);
    const eq = s.indexOf("=");
    if (eq > 0) map[s.slice(0, eq).trim()] = s.slice(eq + 1).trim();
  }
  const setVoice = (voice, name) => {
    const next = VOICES
      .map((v) => [v, v === voice ? name : map[v]])
      .filter(([, n]) => n)
      .map(([v, n]) => `${v}=${n}`);
    onChange(next);
  };
  return (
    <div className="voice-instruments">
      {VOICES.map((voice) => (
        <div className="voice-row" key={voice}>
          <span className="voice-name">{voice}</span>
          <input
            className="textfield mono" list="instrument-list"
            value={map[voice] || ""} spellCheck={false}
            placeholder="(same as main)"
            onChange={(e) => setVoice(voice, e.target.value)}
          />
          {map[voice] && (
            <button className="preview-btn" title={`preview ${voice}`}
              onClick={() => onPreview(map[voice])}>▶</button>
          )}
        </div>
      ))}
    </div>
  );
}

function Param({ param, value, onChange, grooves, instruments, instrumentCatalog,
                onPreviewInstrument, previewing }) {
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
        <InstrumentPicker value={value} instruments={instruments}
          catalog={instrumentCatalog} onChange={onChange}
          onPreview={onPreviewInstrument} previewing={previewing} />
      </div>
    );
  }
  if (param.name === "voice_instrument") {
    return (
      <div className="param wide">
        <div className="param-label">
          <span>{pretty(param.name)}</span>
          {param.help && <span className="info" data-tip={param.help} tabIndex={0} role="button" aria-label={param.help}>?</span>}
        </div>
        <VoiceInstrumentPicker value={value} instruments={instruments}
          onChange={onChange} onPreview={onPreviewInstrument} />
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
