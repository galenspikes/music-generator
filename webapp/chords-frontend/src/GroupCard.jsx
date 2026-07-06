// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// A `[a,b,c]*N` chord group — the same repeat/chain grouping already
// available in the raw token grammar, built here by tapping instead of
// typing brackets. Nested chords reuse ChordCard unchanged (it doesn't know
// or care whether it's top-level or inside a group).
import React from "react";
import ChordCard from "./ChordCard.jsx";
import Stepper from "./Stepper.jsx";

export default function GroupCard({
  anchorId,
  block,
  recipes,
  parsed,
  modeById,
  onModeChange,
  activeId,
  onStrikeChord,
  onCreateChord,
  makeRandomFields,
  randomMode,
  onRandomizeGroup,
  onPreview,
  onChangeGroup,
  onRemoveGroup,
  onMoveUp,
  onMoveDown,
  canMoveUp,
  canMoveDown,
}) {
  const chords = block.chords;
  const parsedChords = (parsed && parsed.type === "group" && parsed.chords) || [];

  const setChord = (i, patch) =>
    onChangeGroup({ chords: chords.map((c, j) => (j === i ? { ...c, ...patch } : c)) });
  const addChord = () => onChangeGroup({ chords: [...chords, onCreateChord()] });
  const removeChord = (i) => onChangeGroup({ chords: chords.filter((_, j) => j !== i) });
  const randomizeMember = (i, id) => {
    setChord(i, makeRandomFields());
    onModeChange(id, randomMode());
  };
  const moveChord = (i, dir) => {
    const next = [...chords];
    const [item] = next.splice(i, 1);
    next.splice(i + dir, 0, item);
    onChangeGroup({ chords: next });
  };

  return (
    <div className="chord-card group-card" id={anchorId}>
      <div className="card-top">
        <button className="strike-btn" onClick={onPreview} disabled={!parsedChords.length} aria-label="Preview group">
          ▸
        </button>
        <span className="card-chord-label">group</span>
        <Stepper value={block.rep} min={1} onChange={(rep) => onChangeGroup({ rep })} />
        <div className="card-reorder">
          <button className="mini-btn" onClick={onRandomizeGroup} aria-label="Randomize this group" title="Randomize this group">
            🎲
          </button>
          <button className="mini-btn" onClick={onMoveUp} disabled={!canMoveUp} aria-label="Move earlier">
            ↑
          </button>
          <button className="mini-btn" onClick={onMoveDown} disabled={!canMoveDown} aria-label="Move later">
            ↓
          </button>
          <button className="mini-btn danger" onClick={onRemoveGroup} aria-label="Remove group">
            ×
          </button>
        </div>
      </div>
      <div className="group-inner">
        {chords.map((c, i) => (
          <ChordCard
            key={c.id}
            block={c}
            recipes={recipes}
            parsed={parsedChords[i]}
            mode={modeById[c.id] || "strike"}
            onModeChange={(m) => onModeChange(c.id, m)}
            active={activeId === c.id}
            onStrike={() => onStrikeChord(c, parsedChords[i])}
            onChange={(patch) => setChord(i, patch)}
            onRandomize={() => randomizeMember(i, c.id)}
            onRemove={() => removeChord(i)}
            onMoveUp={() => moveChord(i, -1)}
            onMoveDown={() => moveChord(i, 1)}
            canMoveUp={i > 0}
            canMoveDown={i < chords.length - 1}
          />
        ))}
        <button className="add-chord-btn small" onClick={addChord}>
          + chord to group
        </button>
      </div>
    </div>
  );
}
