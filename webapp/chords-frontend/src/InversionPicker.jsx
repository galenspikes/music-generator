// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// A tap pill row for chord inversion, replacing a digit-filtered text input.
// "root" is root position (bass = the root). Inversions 1..N put a higher
// chord tone in the bass. Inversion 0 is intentionally omitted: it puts the
// root in the bass too, so it's identical to root position (see
// tokens.parse_colon_key_token) — showing both was just confusing.
import React from "react";

export default function InversionPicker({ value, maxInversion, onChange }) {
  const options = [];
  for (let n = 1; n <= maxInversion; n++) options.push(n);
  // Treat empty / null / 0 all as "root position" so older saved data with an
  // explicit 0 still highlights the root pill.
  const num = value === "" || value == null ? null : Number(value);
  const current = num === 0 ? null : num;
  return (
    <div className="inv-picker">
      <span className="inv-label">Inv</span>
      <div className="pill-row">
        <button
          className={"pill" + (current === null ? " on" : "")}
          onClick={() => onChange("")}
          title="Root position — the root note is in the bass"
        >
          root
        </button>
        {options.map((n) => (
          <button
            key={n}
            className={"pill" + (current === n ? " on" : "")}
            onClick={() => onChange(String(n))}
            title={`${n}${n === 1 ? "st" : n === 2 ? "nd" : n === 3 ? "rd" : "th"} inversion`}
          >
            {n}
          </button>
        ))}
      </div>
    </div>
  );
}
