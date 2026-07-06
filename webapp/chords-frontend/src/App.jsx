// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// Standalone ChordBuilder instrument (powered by Music Generator): a
// tap-driven progression builder plus a saved-progression library, sharing
// the FastAPI backend used by the main song-generator webapp but otherwise
// independent of it.
import React, { useEffect, useRef, useState } from "react";
import Builder from "./Builder.jsx";
import Library from "./Library.jsx";
import SaveDialog from "./SaveDialog.jsx";
import { fetchRecipes, saveProgression, deleteProgression, listProgressions } from "@shared/api.js";
import { INSTRUMENTS } from "./audio.js";

const DRAFT_KEY = "chords_draft_v1";
const INSTRUMENT_KEY = "chords_instrument_v1";
const DEFAULT_BPM = 96;

function slugify(name) {
  return (
    name
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "untitled"
  );
}

// "2026-07-05 new #3" — scoped to today's date, counting up from whatever's
// already saved under today so re-opening Save repeatedly doesn't collide.
function suggestDefaultTitle(existingTitles) {
  const today = new Date().toISOString().slice(0, 10);
  const prefix = `${today} new #`;
  const used = existingTitles
    .filter((t) => t.startsWith(prefix))
    .map((t) => parseInt(t.slice(prefix.length), 10))
    .filter((n) => !isNaN(n));
  const next = used.length ? Math.max(...used) + 1 : 1;
  return `${prefix}${next}`;
}

// The current in-progress progression persists to localStorage (separate
// from the explicit Save-to-Library flow) so a reload or PWA relaunch
// resumes where you left off instead of silently losing unsaved work.
function loadDraft() {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    if (!raw) return null;
    const d = JSON.parse(raw);
    return typeof d.keys === "string" ? d : null;
  } catch {
    return null;
  }
}

function loadInstrument() {
  try {
    const v = localStorage.getItem(INSTRUMENT_KEY);
    return INSTRUMENTS.some((i) => i.id === v) ? v : INSTRUMENTS[0].id;
  } catch {
    return INSTRUMENTS[0].id;
  }
}

export default function App() {
  const [tab, setTab] = useState("build");
  const [recipes, setRecipes] = useState([]);
  const [instrumentId, setInstrumentId] = useState(loadInstrument);

  const draft = useRef(loadDraft()).current;

  // `loaded` holds what the Builder should initialize from; bumping loadNonce
  // remounts the Builder (via a React `key`) so it re-reads these on an
  // explicit Load/New — NOT on every render, which is what previously made
  // switching to the Library tab and back silently drop in-progress edits
  // (Builder/Library used to be conditionally rendered, so switching tabs
  // unmounted Builder entirely; now both stay mounted and are just hidden
  // via CSS, so Builder's internal state survives the trip).
  const [loaded, setLoaded] = useState(() => ({
    keys: draft?.keys || "",
    title: draft?.title || "",
    tags: draft?.tags || [],
  }));
  const [bpm, setBpm] = useState(draft?.bpm || DEFAULT_BPM);
  const [currentName, setCurrentName] = useState(draft?.currentName || null);
  const [savedSnapshot, setSavedSnapshot] = useState(draft?.savedSnapshot || null);
  const [loadNonce, setLoadNonce] = useState(0);
  const [currentKeys, setCurrentKeys] = useState(loaded.keys);
  const [saveOpen, setSaveOpen] = useState(false);
  const [suggestedTitle, setSuggestedTitle] = useState("");
  const [titleHint, setTitleHint] = useState("");
  const [confirmNew, setConfirmNew] = useState(false);
  const draftTimer = useRef(null);

  useEffect(() => {
    fetchRecipes().then(setRecipes).catch(() => {});
  }, []);

  useEffect(() => {
    localStorage.setItem(INSTRUMENT_KEY, instrumentId);
  }, [instrumentId]);

  useEffect(() => {
    clearTimeout(draftTimer.current);
    draftTimer.current = setTimeout(() => {
      localStorage.setItem(
        DRAFT_KEY,
        JSON.stringify({
          keys: currentKeys,
          title: loaded.title,
          tags: loaded.tags,
          bpm,
          currentName,
          savedSnapshot,
        })
      );
    }, 500);
    return () => clearTimeout(draftTimer.current);
  }, [currentKeys, loaded.title, loaded.tags, bpm, currentName, savedSnapshot]);

  // Only meaningful once something's actually been saved (currentName set) —
  // a brand-new never-saved draft is always just labeled "new progression",
  // not flagged dirty against nothing.
  const dirty =
    !!currentName &&
    !!savedSnapshot &&
    (currentKeys !== savedSnapshot.keys ||
      loaded.title !== savedSnapshot.title ||
      bpm !== savedSnapshot.bpm ||
      JSON.stringify(loaded.tags) !== JSON.stringify(savedSnapshot.tags));

  const handleLoad = (progression) => {
    const nextBpm = progression.tempo || DEFAULT_BPM;
    const tags = progression.tags || [];
    setLoaded({ keys: progression.keys, title: progression.title, tags });
    setBpm(nextBpm);
    setCurrentName(progression.name);
    setSavedSnapshot({ keys: progression.keys, title: progression.title, tags, bpm: nextBpm });
    setLoadNonce((n) => n + 1);
    setTab("build");
  };

  // Saving is an update-in-place when the title still slugifies to the
  // progression's current name; if the title changed, that's a rename (save
  // under the new slug, delete the old one) unless the user explicitly asked
  // to keep both via "save as a new copy".
  const handleSave = ({ title, tags, asNew }) => {
    const name = slugify(title);
    saveProgression(name, { keys: currentKeys, title, tags, tempo: bpm }).then(() => {
      const renaming = !asNew && currentName && name !== currentName;
      const cleanup = renaming ? deleteProgression(currentName) : Promise.resolve();
      cleanup.finally(() => {
        setSaveOpen(false);
        setLoaded((l) => ({ ...l, title, tags }));
        setCurrentName(name);
        setSavedSnapshot({ keys: currentKeys, title, tags, bpm });
      });
    });
  };

  // Fetches the current library's titles to pick the next "yyyy-mm-dd new #n"
  // before opening the dialog, so the default is already correct when it
  // appears (rather than patching it in after the dialog is already open).
  const handleSaveRequest = async (hint) => {
    setTitleHint(hint || "");
    try {
      const items = await listProgressions();
      setSuggestedTitle(suggestDefaultTitle(items.map((p) => p.title || "")));
    } catch {
      setSuggestedTitle(suggestDefaultTitle([]));
    }
    setSaveOpen(true);
  };

  const startNew = () => {
    setLoaded({ keys: "", title: "", tags: [] });
    setBpm(DEFAULT_BPM);
    setCurrentName(null);
    setSavedSnapshot(null);
    setLoadNonce((n) => n + 1);
    setConfirmNew(false);
    setTab("build");
  };

  const handleNewClick = () => (dirty ? setConfirmNew(true) : startNew());

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-brand">
          <span className="app-title">ChordBuilder</span>
          <span className="app-subtitle">powered by Music Generator</span>
        </div>
        <nav className="app-tabs">
          <button className={"app-tab" + (tab === "build" ? " on" : "")} onClick={() => setTab("build")}>
            Build
          </button>
          <button className={"app-tab" + (tab === "library" ? " on" : "")} onClick={() => setTab("library")}>
            Library
          </button>
        </nav>
      </header>

      {tab === "build" && (
        <div className="build-status">
          <span className="build-status-name">
            {currentName ? loaded.title : "new progression"}
            {dirty && (
              <span className="dirty-dot" title="unsaved changes">
                {" "}
                •
              </span>
            )}
          </span>
          {confirmNew ? (
            <span className="new-confirm">
              discard unsaved changes?
              <button className="mini-btn danger" onClick={startNew}>
                yes
              </button>
              <button className="mini-btn" onClick={() => setConfirmNew(false)}>
                cancel
              </button>
            </span>
          ) : (
            <button className="new-btn" onClick={handleNewClick}>
              + new
            </button>
          )}
        </div>
      )}

      <main className="app-main">
        <div className={tab === "build" ? "" : "tab-hidden"}>
          <Builder
            key={loadNonce}
            initialKeys={loaded.keys}
            recipes={recipes}
            instrumentId={instrumentId}
            setInstrumentId={setInstrumentId}
            bpm={bpm}
            setBpm={setBpm}
            onKeysChange={setCurrentKeys}
            onSaveRequest={handleSaveRequest}
          />
        </div>
        <div className={tab === "library" ? "" : "tab-hidden"}>
          <Library onLoad={handleLoad} currentName={currentName} active={tab === "library"} />
        </div>
      </main>

      <SaveDialog
        open={saveOpen}
        onClose={() => setSaveOpen(false)}
        onSave={handleSave}
        defaultTitle={loaded.title || suggestedTitle}
        titleHint={titleHint}
        defaultTags={loaded.tags}
        isExisting={!!currentName}
      />

      <footer className="app-footer">
        <a href="https://galenspikes.github.io/music-generator/" target="_blank" rel="noreferrer">home</a> ·{" "}
        <a href="https://gsp87-music-generator.hf.space/" target="_blank" rel="noreferrer">full instrument</a> ·{" "}
        <a href="https://galenspikes.github.io/music-generator/chords.html" target="_blank" rel="noreferrer">
          chord reference
        </a>{" "}
        · <a href="https://github.com/galenspikes/music-generator" target="_blank" rel="noreferrer">github</a>
      </footer>
    </div>
  );
}
