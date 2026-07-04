// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// A generic bottom-sheet popup: tap a chip/button to open, tap the backdrop
// or a choice to close. The one interaction primitive every picker below is
// built on, so chord data entry is always tap-driven, never typed.
import React from "react";

export default function Sheet({ open, onClose, title, children }) {
  if (!open) return null;
  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-head">
          <span className="sheet-title">{title}</span>
          <button className="sheet-close" onClick={onClose} aria-label="Close">×</button>
        </div>
        <div className="sheet-body">{children}</div>
      </div>
    </div>
  );
}
