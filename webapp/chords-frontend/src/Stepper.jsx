// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// "− N +" stepper for open-ended numeric values (repeat count, tempo),
// replacing <input type="number">.
import React from "react";

export default function Stepper({ value, onChange, min = 1, max = Infinity, step = 1, label = "×" }) {
  const dec = () => onChange(Math.max(min, value - step));
  const inc = () => onChange(Math.min(max, value + step));
  return (
    <div className="stepper">
      <span className="stepper-label">{label}</span>
      <button className="stepper-btn" onClick={dec} disabled={value <= min} aria-label={`Decrease ${label}`}>
        −
      </button>
      <span className="stepper-value">{value}</span>
      <button className="stepper-btn" onClick={inc} disabled={value >= max} aria-label={`Increase ${label}`}>
        +
      </button>
    </div>
  );
}
