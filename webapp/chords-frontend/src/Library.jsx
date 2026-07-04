// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// Browsable/searchable grid of saved chord progressions ("patches"): load,
// delete. Renaming isn't a separate endpoint (the full-song preset system
// doesn't have one either) — save under a new title to create a new entry,
// then delete the old one from here.
import React, { useEffect, useState } from "react";
import { listProgressions, deleteProgression, parseKeys } from "@shared/api.js";

function segmentLabels(segments) {
  return (segments || []).map((s) =>
    s.type === "group" ? `[${s.chords.map((c) => c.label).join(" ")}]×${s.reps}` : s.label
  );
}

export default function Library({ onLoad }) {
  const [items, setItems] = useState([]);
  const [labelsByName, setLabelsByName] = useState({});
  const [confirmDelete, setConfirmDelete] = useState(null);

  const refresh = () => listProgressions().then(setItems).catch(() => {});
  useEffect(() => {
    refresh();
  }, []);

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

  return (
    <div className="library">
      {items.length === 0 && (
        <div className="library-empty">No saved progressions yet — build one and tap Save to Library.</div>
      )}
      <div className="library-grid">
        {items.map((p) => (
          <div className="library-card" key={p.name}>
            <div className="library-card-head">
              <span className="library-card-title">{p.title}</span>
              {p.tempo != null && <span className="library-card-tempo">{p.tempo} bpm</span>}
            </div>
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
