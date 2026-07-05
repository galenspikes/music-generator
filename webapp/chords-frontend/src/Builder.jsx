// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// The progression-building screen: a tap-driven list of chord cards (and
// [a,b,c]*N groups), a transport to preview the whole progression, and a
// save entry point into the library. No text/number entry for chord data
// anywhere in this tree.
import React, { useEffect, useRef, useState } from "react";
import ChordCard from "./ChordCard.jsx";
import GroupCard from "./GroupCard.jsx";
import { parseKeys } from "@shared/api.js";
import { splitTopLevel, parseToken, blocksToKeys, defaultChordBlock, defaultGroupBlock } from "./tokenFormat.js";
import { realizeChord } from "./chordNotes.js";
import { playChord, playSustain, playArpeggio, playProgression, stopAll, INSTRUMENTS } from "./audio.js";
import Stepper from "./Stepper.jsx";
import { summarizeSegments } from "./segmentLabels.js";

const MIN_BPM = 40;
const MAX_BPM = 220;
// Sanity cap on how many chords a single "Play progression" tap will
// schedule — a progression can legitimately expand to thousands of chords
// (e.g. a *1000 repeat), which would hang the browser's timer queue rather
// than usefully "preview" anything.
const MAX_PLAYBACK_CHORDS = 300;

export default function Builder({
  initialKeys,
  recipes,
  instrumentId,
  setInstrumentId,
  bpm,
  setBpm,
  onKeysChange,
  onSaveRequest,
}) {
  const [blocks, setBlocks] = useState(() => splitTopLevel(initialKeys || "").map(parseToken));
  const [parsed, setParsed] = useState({ ok: true, chords: [], segments: [] });
  const [modeById, setModeById] = useState({});
  const [activeId, setActiveId] = useState(null);
  const [arpeggiate, setArpeggiate] = useState(false);
  const [loopProgression, setLoopProgression] = useState(false);
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
  const addGroup = () => setBlocks((bs) => [...bs, defaultGroupBlock()]);
  const removeBlock = (i) => setBlocks((bs) => bs.filter((_, j) => j !== i));
  const moveBlock = (i, dir) =>
    setBlocks((bs) => {
      const next = [...bs];
      const [item] = next.splice(i, 1);
      next.splice(i + dir, 0, item);
      return next;
    });

  const segments = parsed.ok ? parsed.segments : [];

  const stopEverything = () => {
    stopAll();
    setActiveId(null);
  };

  const setMode = (id, mode) => setModeById((mm) => ({ ...mm, [id]: mode }));

  // Strikes a single chord (top-level or nested inside a group) according to
  // its own Strike/Sustain/Arpeggio/Loop mode.
  const triggerChord = (block, parsedChord) => {
    if (!parsedChord || block.kind !== "chord") return;
    const mode = modeById[block.id] || "strike";
    const notes = realizeChord(parsedChord);
    if (mode === "strike") {
      playChord(notes, { instrumentId });
      setActiveId(null);
    } else if (mode === "arpeggio") {
      playArpeggio(notes, { instrumentId, loop: false });
      setActiveId(null);
    } else {
      // sustain / loop: tapping again stops it.
      if (activeId === block.id) {
        stopEverything();
      } else {
        if (mode === "sustain") playSustain(notes, { instrumentId });
        else playArpeggio(notes, { instrumentId, loop: true });
        setActiveId(block.id);
      }
    }
  };

  // A raw (unparseable) top-level token — best-effort preview only.
  const triggerRaw = (parsedChord) => {
    if (!parsedChord) return;
    if (parsedChord.type === "group" && parsedChord.chords) {
      playProgression(
        parsedChord.chords.map((c) => ({ notes: realizeChord(c) })),
        { instrumentId, bpm: 160 }
      );
    } else {
      playChord(realizeChord(parsedChord), { instrumentId });
    }
    setActiveId(null);
  };

  // Previews one pass through a group's own chords (ignores the group's own
  // repeat count — that's what "Play progression" is for).
  const previewGroup = (parsedGroup) => {
    if (!parsedGroup || !parsedGroup.chords) return;
    setActiveId(null);
    playProgression(
      parsedGroup.chords.map((c) => ({ notes: realizeChord(c) })),
      { instrumentId, bpm: 160 }
    );
  };

  // The whole progression, exactly as the real engine would expand it —
  // `parsed.chords` already honors every *N and [group]*N repeat (it's the
  // same expansion `music_generator` uses), so setting a repeat count here
  // actually changes what plays.
  const playAll = () => {
    const chords = (parsed.chords || []).slice(0, MAX_PLAYBACK_CHORDS);
    if (!chords.length) return;
    setActiveId(null);
    playProgression(
      chords.map((c) => ({ notes: realizeChord(c) })),
      { instrumentId, bpm, arpeggiate, loop: loopProgression }
    );
  };

  const truncated = (parsed.chords || []).length > MAX_PLAYBACK_CHORDS;

  return (
    <div className="builder">
      <div className="builder-transport">
        <button className="transport-btn play" onClick={playAll} disabled={!(parsed.chords || []).length}>
          ▸ Play progression
        </button>
        <button className="transport-btn stop" onClick={stopEverything}>
          ■ Stop
        </button>
        <button
          className={"transport-btn transport-toggle" + (loopProgression ? " on" : "")}
          onClick={() => setLoopProgression((v) => !v)}
        >
          ⟳ Loop
        </button>
        <button
          className={"transport-btn transport-toggle" + (arpeggiate ? " on" : "")}
          onClick={() => setArpeggiate((a) => !a)}
        >
          Arpeggiate
        </button>
        <Stepper value={bpm} min={MIN_BPM} max={MAX_BPM} step={4} label="bpm" onChange={setBpm} />
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
      {parsed.ok && parsed.chords && parsed.chords.length > 0 && (
        <div className="builder-note">
          plays {parsed.chords.length} chord{parsed.chords.length === 1 ? "" : "s"}
        </div>
      )}
      {truncated && (
        <div className="builder-note">
          Progression expands to {parsed.chords.length} chords — playback previews the first {MAX_PLAYBACK_CHORDS}.
        </div>
      )}

      <div className="builder-cards">
        {blocks.map((b, i) =>
          b.kind === "group" ? (
            <GroupCard
              key={b.id}
              block={b}
              recipes={recipes}
              parsed={segments[i]}
              modeById={modeById}
              onModeChange={setMode}
              activeId={activeId}
              onStrikeChord={triggerChord}
              onPreview={() => previewGroup(segments[i])}
              onChangeGroup={(patch) => setBlock(i, patch)}
              onRemoveGroup={() => removeBlock(i)}
              onMoveUp={() => moveBlock(i, -1)}
              onMoveDown={() => moveBlock(i, 1)}
              canMoveUp={i > 0}
              canMoveDown={i < blocks.length - 1}
            />
          ) : (
            <ChordCard
              key={b.id}
              block={b}
              recipes={recipes}
              parsed={segments[i]}
              mode={modeById[b.id] || "strike"}
              onModeChange={(m) => setMode(b.id, m)}
              active={activeId === b.id}
              onStrike={() => (b.kind === "raw" ? triggerRaw(segments[i]) : triggerChord(b, segments[i]))}
              onChange={(patch) => setBlock(i, patch)}
              onRemove={() => removeBlock(i)}
              onMoveUp={() => moveBlock(i, -1)}
              onMoveDown={() => moveBlock(i, 1)}
              canMoveUp={i > 0}
              canMoveDown={i < blocks.length - 1}
            />
          )
        )}
        <div className="add-row">
          <button className="add-chord-btn" onClick={addChord}>
            + chord
          </button>
          <button className="add-chord-btn" onClick={addGroup}>
            + group
          </button>
        </div>
      </div>

      <button
        className="save-btn"
        onClick={() => onSaveRequest(summarizeSegments(segments))}
        disabled={!blocks.length}
      >
        Save to Library
      </button>
    </div>
  );
}
