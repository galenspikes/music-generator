// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// A tap pill row for chord inversion, replacing a digit-filtered text input.
// Bounded by the chord's note count (an inversion beyond that just repeats),
// so this always shows a small, sane set of choices.
import React from "react";

export default function InversionPicker({ value, maxInversion, onChange }) {
  const options = Array.from({ length: Math.max(1, maxInversion + 1) }, (_, i) => i);
  const current = value === "" || value == null ? null : Number(value);
  return (
    <div className="inv-picker">
      <span className="inv-label">Inv</span>
      <div className="pill-row">
        <button className={"pill" + (current === null ? " on" : "")} onClick={() => onChange("")}>
          root
        </button>
        {options.map((n) => (
          <button key={n} className={"pill" + (current === n ? " on" : "")} onClick={() => onChange(String(n))}>
            {n}
          </button>
        ))}
      </div>
    </div>
  );
}
