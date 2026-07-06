// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// Browsable/searchable grid of saved chord progressions ("patches"): load,
// delete. Renaming isn't a separate endpoint (the full-song preset system
// doesn't have one either) — save under a new title to create a new entry,
// then delete the old one from here.
import React, { useEffect, useMemo, useState } from "react";
import { listProgressions, deleteProgression, parseKeys } from "@shared/api.js";
import { segmentLabels } from "./segmentLabels.js";

function formatSaved(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function Library({ onLoad, currentName, active }) {
  const [items, setItems] = useState([]);
  const [labelsByName, setLabelsByName] = useState({});
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [search, setSearch] = useState("");

  const refresh = () =>
    listProgressions()
      .then((list) => setItems([...list].sort((a, b) => (b.saved || "").localeCompare(a.saved || ""))))
      .catch(() => {});

  // Re-fetch whenever this tab becomes active (not just on first mount) —
  // Builder and Library both stay mounted now (see App.jsx) so a save made
  // while this tab was hidden needs to show up when you switch back to it.
  useEffect(() => {
    if (active) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  useEffect(() => {
    items.forEach((p) => {
      if (labelsByName[p.name]) return;
      parseKeys(p.keys)
        .then((r) => setLabelsByName((m) => ({ ...m, [p.name]: segmentLabels(r.segments) })))
        .catch(() => {});
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items]);

  const handleDelete = (name) => {
    deleteProgression(name).then(refresh);
    setConfirmDelete(null);
  };

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (p) => p.title.toLowerCase().includes(q) || (p.tags || []).some((t) => t.toLowerCase().includes(q))
    );
  }, [items, search]);

  return (
    <div className="library">
      {items.length > 0 && (
        <input
          className="library-search"
          type="search"
          placeholder="search by title or tag…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      )}
      {items.length === 0 && (
        <div className="library-empty">No saved progressions yet — build one and tap Save to Library.</div>
      )}
      {items.length > 0 && filtered.length === 0 && (
        <div className="library-empty">no progressions match "{search}"</div>
      )}
      <div className="library-grid">
        {filtered.map((p) => (
          <div className={"library-card" + (p.name === currentName ? " current" : "")} key={p.name}>
            <div className="library-card-head">
              <span className="library-card-title">
                {p.title}
                {p.name === currentName && <span className="current-badge">editing</span>}
              </span>
              {p.tempo != null && <span className="library-card-tempo">{p.tempo} bpm</span>}
            </div>
            {p.saved && <div className="library-card-saved">saved {formatSaved(p.saved)}</div>}
            <div className="library-card-chips">
              {(labelsByName[p.name] || []).map((l, i) => (
                <span className="mini-chip" key={i}>
                  {l}
                </span>
              ))}
            </div>
            {p.tags && p.tags.length > 0 && (
              <div className="library-card-tags">
                {p.tags.map((t) => (
                  <span className="tag-chip" key={t}>
                    {t}
                  </span>
                ))}
              </div>
            )}
            <div className="library-card-actions">
              <button className="lib-load-btn" onClick={() => onLoad(p)}>
                Load
              </button>
              {confirmDelete === p.name ? (
                <>
                  <button className="lib-delete-confirm" onClick={() => handleDelete(p.name)}>
                    Confirm delete
                  </button>
                  <button className="lib-delete-cancel" onClick={() => setConfirmDelete(null)}>
                    Cancel
                  </button>
                </>
              ) : (
                <button className="lib-delete-btn" onClick={() => setConfirmDelete(p.name)}>
                  Delete
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
