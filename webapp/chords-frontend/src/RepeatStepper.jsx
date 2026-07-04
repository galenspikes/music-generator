// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// "− N +" stepper for repeat count, replacing <input type="number">. Repeat
// is genuinely open-ended, so a stepper (not a fixed pill set) is the right
// control here.
import React from "react";

export default function RepeatStepper({ value, onChange, min = 1 }) {
  const dec = () => onChange(Math.max(min, value - 1));
  const inc = () => onChange(value + 1);
  return (
    <div className="stepper">
      <span className="stepper-label">×</span>
      <button className="stepper-btn" onClick={dec} disabled={value <= min} aria-label="Decrease repeat count">
        −
      </button>
      <span className="stepper-value">{value}</span>
      <button className="stepper-btn" onClick={inc} aria-label="Increase repeat count">
        +
      </button>
    </div>
  );
}
