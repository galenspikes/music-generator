// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// A HUD strip pinned to the top of the Build screen: what's playing right now
// (chord, position in the progression, and its playback mode) when audio is
// running, or a ready/empty status otherwise, plus the current instrument and
// tempo. Fed by Builder's playback state (see onStatus).
import React from "react";

const MODE_LABEL = { strike: "strike", sustain: "sustain", arpeggio: "arp", loop: "loop" };

export default function Monitor({ playing, label, pos, total, mode, stepCount, instrumentLabel, bpm }) {
  return (
    <div className={"monitor" + (playing ? " playing" : "")}>
      <span className={"monitor-lamp" + (playing ? " on" : "")} aria-hidden="true" />
      <div className="monitor-main">
        {playing && label ? (
          <>
            <span className="monitor-chord">{label}</span>
            {mode && <span className="monitor-mode">{MODE_LABEL[mode] || mode}</span>}
            {total > 1 && (
              <span className="monitor-pos">
                {pos + 1}/{total}
              </span>
            )}
          </>
        ) : (
          <span className="monitor-idle">
            {stepCount ? `${stepCount} chord${stepCount === 1 ? "" : "s"} · ready` : "empty — add a chord"}
          </span>
        )}
      </div>
      <span className="monitor-meta">
        {instrumentLabel} · {bpm} bpm
      </span>
    </div>
  );
}
