// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// Standalone Chord Recipes instrument: a tap-driven progression builder plus
// a saved-progression library, sharing the FastAPI backend used by the main
// song-generator webapp but otherwise independent of it.
import React, { useEffect, useState } from "react";
import Builder from "./Builder.jsx";
import Library from "./Library.jsx";
import SaveDialog from "./SaveDialog.jsx";
import { fetchRecipes, saveProgression } from "@shared/api.js";
import { INSTRUMENTS } from "./audio.js";

function slugify(name) {
  return (
    name
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "untitled"
  );
}

export default function App() {
  const [tab, setTab] = useState("build");
  const [recipes, setRecipes] = useState([]);
  const [instrumentId, setInstrumentId] = useState(INSTRUMENTS[0].id);

  // `loaded` holds what the Builder should initialize from; bumping loadNonce
  // remounts the Builder (via a React `key`) so it re-reads these on load
  // instead of fighting in-progress edits.
  const [loaded, setLoaded] = useState({ keys: "", title: "", tags: [] });
  const [loadNonce, setLoadNonce] = useState(0);
  const [currentKeys, setCurrentKeys] = useState("");
  const [saveOpen, setSaveOpen] = useState(false);

  useEffect(() => {
    fetchRecipes().then(setRecipes).catch(() => {});
  }, []);

  const handleLoad = (progression) => {
    setLoaded({ keys: progression.keys, title: progression.title, tags: progression.tags || [] });
    setLoadNonce((n) => n + 1);
    setTab("build");
  };

  const handleSave = ({ title, tags }) => {
    const name = slugify(title);
    saveProgression(name, { keys: currentKeys, title, tags }).then(() => {
      setSaveOpen(false);
      setLoaded((l) => ({ ...l, title, tags }));
    });
  };

  return (
    <div className="app">
      <header className="app-header">
        <span className="app-title">Chord Recipes</span>
        <nav className="app-tabs">
          <button className={"app-tab" + (tab === "build" ? " on" : "")} onClick={() => setTab("build")}>
            Build
          </button>
          <button className={"app-tab" + (tab === "library" ? " on" : "")} onClick={() => setTab("library")}>
            Library
          </button>
        </nav>
      </header>

      <main className="app-main">
        {tab === "build" ? (
          <Builder
            key={loadNonce}
            initialKeys={loaded.keys}
            recipes={recipes}
            instrumentId={instrumentId}
            setInstrumentId={setInstrumentId}
            onKeysChange={setCurrentKeys}
            onSaveRequest={() => setSaveOpen(true)}
          />
        ) : (
          <Library onLoad={handleLoad} />
        )}
      </main>

      <SaveDialog
        open={saveOpen}
        onClose={() => setSaveOpen(false)}
        onSave={handleSave}
        defaultTitle={loaded.title}
        defaultTags={loaded.tags}
      />
    </div>
  );
}
