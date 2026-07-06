// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// A horizontally-scrollable overview of the whole progression, pinned in the
// top deck — one chip per top-level chord/group. Tapping a chip jumps to that
// card, so navigating a long progression doesn't mean scrolling and hunting.
// Shown only once a progression is long enough to be worth navigating.
import React from "react";

const MIN_BLOCKS = 4;

export default function ChartStrip({ blocks }) {
  if (!blocks || blocks.length < MIN_BLOCKS) return null;
  const jump = (id) => {
    const el = document.getElementById("chord-card-" + id);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  };
  return (
    <div className="chart-strip">
      {blocks.map((b, i) => (
        <button key={b.id} className="chart-chip" onClick={() => jump(b.id)} title={b.label}>
          <span className="chart-chip-num">{i + 1}</span>
          <span className="chart-chip-label">{b.label}</span>
        </button>
      ))}
    </div>
  );
}
