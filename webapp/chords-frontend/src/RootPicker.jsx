// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// Tap-driven root-note picker: a chip that opens a 12-button grid, replacing
// a <select> so mobile users tap instead of opening a native dropdown.
import React, { useState } from "react";
import Sheet from "./Sheet.jsx";
import { ROOTS } from "./tokenFormat.js";

export default function RootPicker({ value, onChange, label = "Root", allowNone = false }) {
  const [open, setOpen] = useState(false);
  const chipClass = "chip " + (allowNone ? "chip-bass" : "chip-root");
  return (
    <>
      <button className={chipClass} onClick={() => setOpen(true)}>
        <span className="chip-label">{label}</span>
        <span className="chip-value">{value || "—"}</span>
      </button>
      <Sheet open={open} onClose={() => setOpen(false)} title={`Choose ${label.toLowerCase()}`}>
        <div className="picker-grid roots-grid">
          {allowNone && (
            <button
              className={"picker-btn" + (!value ? " on" : "")}
              onClick={() => {
                onChange("");
                setOpen(false);
              }}
            >
              none
            </button>
          )}
          {ROOTS.map((r) => (
            <button
              key={r}
              className={"picker-btn" + (value === r ? " on" : "")}
              onClick={() => {
                onChange(r);
                setOpen(false);
              }}
            >
              {r}
            </button>
          ))}
        </div>
      </Sheet>
    </>
  );
}
