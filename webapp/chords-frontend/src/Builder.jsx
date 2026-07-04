// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// The progression-building screen: a tap-driven list of chord cards, a
// transport to preview the whole progression, and a save entry point into
// the library. No text/number entry for chord data anywhere in this tree.
import React, { useEffect, useRef, useState } from "react";
import ChordCard from "./ChordCard.jsx";
import { parseKeys } from "@shared/api.js";
import { splitTopLevel, parseToken, blocksToKeys, defaultChordBlock } from "./tokenFormat.js";
import { realizeChord } from "./chordNotes.js";
import { playProgression, stopAll, INSTRUMENTS } from "./audio.js";

// A group segment's nested chords are exposed once, ignoring both the
// group's and its own repeat counts — the transport previews the shape of
// the progression rather than performing a literal, possibly very long
// (e.g. *16) full playthrough.
function flattenForPreview(segments) {
  const out = [];
  for (const s of segments) {
    if (s.type === "group") out.push(...s.chords);
    else out.push(s);
  }
  return out;
}

export default function Builder({ initialKeys, recipes, instrumentId, setInstrumentId, onKeysChange, onSaveRequest }) {
  const [blocks, setBlocks] = useState(() => splitTopLevel(initialKeys || "").map(parseToken));
  const [parsed, setParsed] = useState({ ok: true, segments: [] });
  const debounce = useRef(null);

  const keys = blocksToKeys(blocks);

  useEffect(() => {
    onKeysChange(keys);
    clearTimeout(debounce.current);
    debounce.current = setTimeout(() => {
      parseKeys(keys).then(setParsed).catch(() => {});
    }, 200);
    return () => clearTimeout(debounce.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keys]);

  const setBlock = (i, patch) => setBlocks((bs) => bs.map((b, j) => (j === i ? { ...b, ...patch } : b)));
  const addChord = () => setBlocks((bs) => [...bs, defaultChordBlock()]);
  const removeBlock = (i) => setBlocks((bs) => bs.filter((_, j) => j !== i));
  const moveBlock = (i, dir) =>
    setBlocks((bs) => {
      const next = [...bs];
      const [item] = next.splice(i, 1);
      next.splice(i + dir, 0, item);
      return next;
    });

  const segments = parsed.ok ? parsed.segments : [];

  const playAll = () => {
    const flat = flattenForPreview(segments);
    if (!flat.length) return;
    playProgression(
      flat.map((c) => ({ notes: realizeChord(c) })),
      { instrumentId, bpm: 96 }
    );
  };

  return (
    <div className="builder">
      <div className="builder-transport">
        <button className="transport-btn play" onClick={playAll} disabled={!segments.length}>
          ▸ Play progression
        </button>
        <button className="transport-btn stop" onClick={stopAll}>
          ■ Stop
        </button>
        <div className="instrument-toggle">
          {INSTRUMENTS.map((inst) => (
            <button
              key={inst.id}
              className={"instrument-btn" + (instrumentId === inst.id ? " on" : "")}
              onClick={() => setInstrumentId(inst.id)}
            >
              {inst.label}
            </button>
          ))}
        </div>
      </div>

      {!parsed.ok && parsed.error && <div className="builder-err">⚠ {parsed.error}</div>}

      <div className="builder-cards">
        {blocks.map((b, i) => (
          <ChordCard
            key={i}
            block={b}
            recipes={recipes}
            parsed={segments[i]}
            instrumentId={instrumentId}
            onChange={(patch) => setBlock(i, patch)}
            onRemove={() => removeBlock(i)}
            onMoveUp={() => moveBlock(i, -1)}
            onMoveDown={() => moveBlock(i, 1)}
            canMoveUp={i > 0}
            canMoveDown={i < blocks.length - 1}
          />
        ))}
        <button className="add-chord-btn" onClick={addChord}>
          + chord
        </button>
      </div>

      <button className="save-btn" onClick={onSaveRequest} disabled={!blocks.length}>
        Save to Library
      </button>
    </div>
  );
}
