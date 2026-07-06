// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// A randomize (🎲) button gated by a padlock, à la macOS System Settings:
// locked by default, so the dice is disabled until you tap the lock to open
// it. This prevents an accidental tap from rerolling a chord/group/everything
// you were happy with. The lock stays open (like macOS) until you tap it shut
// again; it re-locks on reload since each control owns its own state.
import React, { useState } from "react";

export default function RandomizeControl({
  onRandomize,
  label = "",
  lockClass = "mini-btn lock-btn",
  diceClass = "mini-btn dice-btn",
  disabled = false,
}) {
  const [locked, setLocked] = useState(true);
  return (
    <>
      <button
        type="button"
        className={lockClass + (locked ? " locked" : " unlocked")}
        onClick={() => setLocked((l) => !l)}
        aria-label={locked ? `Unlock ${label} randomizer` : `Lock ${label} randomizer`}
        aria-pressed={!locked}
        title={locked ? "Locked — tap to unlock randomize" : "Unlocked — tap to lock"}
      >
        {locked ? "🔒" : "🔓"}
      </button>
      <button
        type="button"
        className={diceClass}
        onClick={onRandomize}
        disabled={locked || disabled}
        aria-label={`Randomize ${label}`}
        title={locked ? "Unlock (🔒) to randomize" : `Randomize ${label}`}
      >
        🎲
      </button>
    </>
  );
}
