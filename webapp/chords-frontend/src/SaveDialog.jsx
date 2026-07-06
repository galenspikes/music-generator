// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// Save-to-library popup. Title is free text (naming a patch is inherently
// textual — the "tap, don't type" rule is about chord *data* entry, not
// human-readable labels); tags are a toggleable chip set plus an optional
// one-off custom tag. When editing an already-saved progression, saving
// updates that entry in place (or renames it, if the title changed) unless
// "save as a new copy" is checked.
import React, { useEffect, useState } from "react";
import Sheet from "./Sheet.jsx";

const CURATED_TAGS = [
  "jazz", "modal", "pop", "rock", "blues", "classical",
  "ambient", "turnaround", "vamp", "ballad",
];

export default function SaveDialog({ open, onClose, onSave, defaultTitle, titleHint, defaultTags, isExisting }) {
  const [title, setTitle] = useState(defaultTitle || "");
  const [tags, setTags] = useState(defaultTags || []);
  const [addingTag, setAddingTag] = useState(false);
  const [customTag, setCustomTag] = useState("");
  const [asNew, setAsNew] = useState(false);

  // Re-sync from the current progression each time the dialog opens — it
  // doesn't remount, so stale state from a previous open would otherwise stick.
  useEffect(() => {
    if (open) {
      setTitle(defaultTitle || "");
      setTags(defaultTags || []);
      setAsNew(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const toggleTag = (t) => setTags((ts) => (ts.includes(t) ? ts.filter((x) => x !== t) : [...ts, t]));

  const commitCustomTag = () => {
    const t = customTag.trim().toLowerCase();
    if (t && !tags.includes(t)) setTags((ts) => [...ts, t]);
    setCustomTag("");
    setAddingTag(false);
  };

  const allTags = Array.from(new Set([...CURATED_TAGS, ...tags]));
  const willUpdate = isExisting && !asNew;

  return (
    <Sheet open={open} onClose={onClose} title={willUpdate ? "Update library entry" : "Save to library"}>
      <label className="save-title-label">
        Title
        <input
          className="save-title-input"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={titleHint || "ii-V-I turnaround"}
          autoFocus
        />
      </label>
      <div className="save-tags-label">Tags</div>
      <div className="pill-row wrap">
        {allTags.map((t) => (
          <button key={t} className={"pill" + (tags.includes(t) ? " on" : "")} onClick={() => toggleTag(t)}>
            {t}
          </button>
        ))}
        {addingTag ? (
          <input
            className="tag-input"
            autoFocus
            value={customTag}
            onChange={(e) => setCustomTag(e.target.value)}
            onBlur={commitCustomTag}
            onKeyDown={(e) => e.key === "Enter" && commitCustomTag()}
            placeholder="new tag"
          />
        ) : (
          <button className="pill add-tag" onClick={() => setAddingTag(true)}>
            + new tag
          </button>
        )}
      </div>
      {isExisting && (
        <label className="asnew-toggle">
          <input type="checkbox" checked={asNew} onChange={(e) => setAsNew(e.target.checked)} />
          Save as a new copy (keep the original too)
        </label>
      )}
      <button
        className="save-confirm-btn"
        disabled={!title.trim()}
        onClick={() => onSave({ title: title.trim(), tags, asNew })}
      >
        {willUpdate ? "Update" : "Save"}
      </button>
    </Sheet>
  );
}
