// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// One chord (or unrecognized/group token, shown read-only) in the progression
// builder. All editable fields are tap-driven popups/pills/steppers — see
// RootPicker, RecipePicker, InversionPicker, RepeatStepper.
import React from "react";
import RootPicker from "./RootPicker.jsx";
import RecipePicker from "./RecipePicker.jsx";
import InversionPicker from "./InversionPicker.jsx";
import Stepper from "./Stepper.jsx";

export const MODES = [
  { id: "strike", label: "Strike" },
  { id: "sustain", label: "Sustain" },
  { id: "arpeggio", label: "Arp" },
  { id: "loop", label: "Loop" },
];

export default function ChordCard({
  block,
  recipes,
  parsed,
  mode,
  onModeChange,
  active,
  onStrike,
  onChange,
  onRemove,
  onMoveUp,
  onMoveDown,
  canMoveUp,
  canMoveDown,
}) {
  const recipeInfo = recipes.find((r) => r.name === block.recipe);
  const maxInversion = recipeInfo ? recipeInfo.intervals.length - 1 : 3;
  const isToggle = mode === "sustain" || mode === "loop";

  const reorderControls = (
    <div className="card-reorder">
      <button className="mini-btn" onClick={onMoveUp} disabled={!canMoveUp} aria-label="Move earlier">
        ↑
      </button>
      <button className="mini-btn" onClick={onMoveDown} disabled={!canMoveDown} aria-label="Move later">
        ↓
      </button>
      <button className="mini-btn danger" onClick={onRemove} aria-label="Remove chord">
        ×
      </button>
    </div>
  );

  if (block.kind === "raw") {
    return (
      <div className="chord-card raw-card">
        <button className="strike-btn" onClick={onStrike} disabled={!parsed} aria-label="Play">
          ▸
        </button>
        <code className="raw-text">{block.text}</code>
        {reorderControls}
      </div>
    );
  }

  return (
    <div className="chord-card">
      <div className="card-top">
        <button
          className={"strike-btn" + (isToggle && active ? " playing" : "")}
          onClick={onStrike}
          disabled={!parsed}
          aria-label={isToggle && active ? "Stop" : "Play chord"}
        >
          {isToggle && active ? "■" : "▸"}
        </button>
        <span className="card-chord-label">{parsed ? parsed.label : "…"}</span>
        {reorderControls}
      </div>
      <div className="card-fields">
        <RootPicker value={block.root} onChange={(root) => onChange({ root })} label="Root" />
        <RecipePicker value={block.recipe} recipes={recipes} onChange={(recipe) => onChange({ recipe, inv: "" })} />
        <InversionPicker value={block.inv} maxInversion={maxInversion} onChange={(inv) => onChange({ inv })} />
        <RootPicker value={block.bass} onChange={(bass) => onChange({ bass })} label="Bass" allowNone />
        <Stepper value={block.rep} onChange={(rep) => onChange({ rep })} />
      </div>
      <div className="mode-row">
        {MODES.map((m) => (
          <button
            key={m.id}
            className={"pill mode-pill" + (mode === m.id ? " on" : "")}
            onClick={() => onModeChange(m.id)}
          >
            {m.label}
          </button>
        ))}
      </div>
    </div>
  );
}
