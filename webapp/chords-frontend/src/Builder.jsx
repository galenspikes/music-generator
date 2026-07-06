// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// The progression-building screen: a tap-driven list of chord cards (and
// [a,b,c]*N groups), a transport to play/preview, and a pinned add/randomize
// action bar. No text/number entry for chord data anywhere in this tree.
// (Save lives in App's sticky top deck; navigation and the playback HUD too.)
import React, { useEffect, useRef, useState } from "react";
import ChordCard from "./ChordCard.jsx";
import GroupCard from "./GroupCard.jsx";
import { parseKeys } from "@shared/api.js";
import { ROOTS, splitTopLevel, parseToken, blocksToKeys, defaultChordBlock, makeId } from "./tokenFormat.js";
import { realizeChord } from "./chordNotes.js";
import { playChord, playSustain, playArpeggio, playProgression, stopAll, INSTRUMENTS } from "./audio.js";
import Stepper from "./Stepper.jsx";
import { summarizeSegments, labelForSegment } from "./segmentLabels.js";

const MIN_BPM = 40;
const MAX_BPM = 220;
// Sanity cap on how many chords a single "Play progression" tap will
// schedule — a progression can legitimately expand to thousands of chords
// (e.g. a *1000 repeat), which would hang the browser's timer queue rather
// than usefully "preview" anything.
const MAX_PLAYBACK_CHORDS = 300;
const MODE_CHOICES = ["strike", "sustain", "arpeggio"];
// Roughly how long a one-shot solo tap sounds, so the HUD clears itself after
// the note fades rather than lingering as if still playing.
const STRIKE_HUD_MS = 1400;
const ARP_STEP_MS = 150;

const randomChoice = (arr) => arr[Math.floor(Math.random() * arr.length)];

// A random root/quality (and sometimes a real inversion — 1..maxInv, never 0,
// which is just root position) for a chord. Shared by "+ chord" and the
// randomize (🎲) buttons.
function randomChordFields(recipes) {
  const chosen = recipes && recipes.length ? randomChoice(recipes) : null;
  const root = randomChoice(ROOTS);
  const recipe = chosen ? chosen.name : "maj7";
  const maxInv = chosen ? Math.max(0, chosen.intervals.length - 1) : 0;
  const inv = maxInv >= 1 && Math.random() < 0.4 ? String(1 + Math.floor(Math.random() * maxInv)) : "";
  return { root, recipe, inv, bass: "" };
}

function randomChordBlock(recipes) {
  return { ...defaultChordBlock(), ...randomChordFields(recipes) };
}

export default function Builder({
  initialKeys,
  recipes,
  instrumentId,
  setInstrumentId,
  bpm,
  setBpm,
  onKeysChange,
  onStatus,
}) {
  const [blocks, setBlocks] = useState(() => splitTopLevel(initialKeys || "").map(parseToken));
  const [parsed, setParsed] = useState({ ok: true, chords: [], segments: [] });
  const [modeById, setModeById] = useState({});
  const [activeId, setActiveId] = useState(null);
  const [live, setLive] = useState(false);
  // The step list currently feeding the HUD, plus the index within it that is
  // sounding right now (-1 = nothing playing). `playSteps` carries labels so
  // the monitor can name each chord as it goes by.
  const [playSteps, setPlaySteps] = useState([]);
  const [playPos, setPlayPos] = useState(-1);
  const debounce = useRef(null);
  const hudTimer = useRef(null);

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
  const setMode = (id, mode) => setModeById((mm) => ({ ...mm, [id]: mode }));

  const addChord = () => {
    const block = randomChordBlock(recipes);
    setBlocks((bs) => [...bs, block]);
    setMode(block.id, randomChoice(MODE_CHOICES));
  };

  // Shared by GroupCard's own "+ chord to group" button, so a chord added
  // inside a group gets the same randomized treatment as a top-level one.
  const createChordForGroup = () => {
    const block = randomChordBlock(recipes);
    setMode(block.id, randomChoice(MODE_CHOICES));
    return block;
  };

  const addGroup = () => {
    const a = randomChordBlock(recipes);
    const b = randomChordBlock(recipes);
    setMode(a.id, randomChoice(MODE_CHOICES));
    setMode(b.id, randomChoice(MODE_CHOICES));
    setBlocks((bs) => [...bs, { kind: "group", id: makeId(), rep: 2, chords: [a, b] }]);
  };

  const removeBlock = (i) => setBlocks((bs) => bs.filter((_, j) => j !== i));
  const moveBlock = (i, dir) =>
    setBlocks((bs) => {
      const next = [...bs];
      const [item] = next.splice(i, 1);
      next.splice(i + dir, 0, item);
      return next;
    });

  const randomMode = () => randomChoice(MODE_CHOICES);

  // Reroll one chord's root/quality/inversion and its playback mode. Works for
  // a top-level chord or (via GroupCard) a chord inside a group.
  const randomizeChordFields = () => randomChordFields(recipes);

  // Reroll every chord in the progression at once (the master 🎲).
  const randomizeAll = () => {
    setBlocks((bs) =>
      bs.map((b) => {
        if (b.kind === "chord") return { ...b, ...randomChordFields(recipes) };
        if (b.kind === "group")
          return { ...b, chords: b.chords.map((c) => ({ ...c, ...randomChordFields(recipes) })) };
        return b;
      })
    );
    setModeById((mm) => {
      const next = { ...mm };
      blocks.forEach((b) => {
        if (b.kind === "chord") next[b.id] = randomMode();
        else if (b.kind === "group") b.chords.forEach((c) => (next[c.id] = randomMode()));
      });
      return next;
    });
  };

  const randomizeBlock = (i) => {
    const b = blocks[i];
    if (b.kind === "chord") {
      setBlock(i, randomChordFields(recipes));
      setMode(b.id, randomMode());
    } else if (b.kind === "group") {
      setBlock(i, { chords: b.chords.map((c) => ({ ...c, ...randomChordFields(recipes) })) });
      b.chords.forEach((c) => setMode(c.id, randomMode()));
    }
  };

  const segments = parsed.ok ? parsed.segments : [];

  // --- HUD helpers ---------------------------------------------------------
  const clearHud = () => {
    clearTimeout(hudTimer.current);
    setPlayPos(-1);
  };
  // One-shot solo tap: name the chord, then clear after it fades.
  const flashHud = (label, mode, ms) => {
    clearTimeout(hudTimer.current);
    setPlaySteps([{ label, mode }]);
    setPlayPos(0);
    hudTimer.current = setTimeout(() => setPlayPos(-1), ms);
  };
  // Held solo (sustain/loop): name the chord and leave it until stopped.
  const holdHud = (label, mode) => {
    clearTimeout(hudTimer.current);
    setPlaySteps([{ label, mode }]);
    setPlayPos(0);
  };

  const stopEverything = () => {
    stopAll();
    setActiveId(null);
    setLive(false);
    clearHud();
  };

  // Strikes a single chord (top-level or nested inside a group) according to
  // its own Strike/Sustain/Arpeggio/Loop mode.
  const triggerChord = (block, parsedChord) => {
    if (!parsedChord || block.kind !== "chord") return;
    const mode = modeById[block.id] || "strike";
    const notes = realizeChord(parsedChord);
    if (mode === "strike") {
      playChord(notes, { instrumentId });
      setActiveId(null);
      flashHud(parsedChord.label, mode, STRIKE_HUD_MS);
    } else if (mode === "arpeggio") {
      playArpeggio(notes, { instrumentId, loop: false });
      setActiveId(null);
      flashHud(parsedChord.label, mode, notes.length * ARP_STEP_MS + STRIKE_HUD_MS);
    } else {
      // sustain: tapping again stops it.
      if (activeId === block.id) {
        stopEverything();
      } else {
        playSustain(notes, { instrumentId });
        setActiveId(block.id);
        holdHud(parsedChord.label, mode);
      }
    }
  };

  // A raw (unparseable-by-the-client) top-level token — best-effort preview
  // only, using whatever the server made of it; no per-chord mode to honor
  // since there's no card UI for it.
  const triggerRaw = (parsedChord) => {
    if (!parsedChord) return;
    setActiveId(null);
    if (parsedChord.type === "group" && parsedChord.chords) {
      const steps = parsedChord.chords.map((c) => ({ notes: realizeChord(c), label: c.label, mode: "strike" }));
      setPlaySteps(steps);
      setPlayPos(0);
      playProgression(steps, { instrumentId, bpm: 160, onStep: setPlayPos, onEnd: clearHud });
    } else {
      playChord(realizeChord(parsedChord), { instrumentId });
      flashHud(parsedChord.label, "strike", STRIKE_HUD_MS);
    }
  };

  // Previews one pass through a group's own chords (ignores the group's own
  // repeat count — that's what "Play progression" is for), honoring each
  // member chord's own programmed mode.
  const previewGroup = (block, parsedGroup) => {
    if (!parsedGroup || !parsedGroup.chords) return;
    setActiveId(null);
    const steps = block.chords
      .map((c, j) => {
        const pc = parsedGroup.chords[j];
        return pc ? { notes: realizeChord(pc), label: pc.label, mode: modeById[c.id] || "strike" } : null;
      })
      .filter(Boolean);
    setPlaySteps(steps);
    setPlayPos(0);
    playProgression(steps, { instrumentId, bpm: 160, onStep: setPlayPos, onEnd: clearHud });
  };

  // Walks `blocks` (which already fully captures every repeat count — a top
  // -level chord's own *N, a group's own *N, and each member chord's own *N
  // inside a group) paired with the matching `segments` entry for pitch
  // data, expanding it into a flat step list where each step carries the
  // originating chord's own programmed Strike/Sustain/Arpeggio/Loop mode and
  // its label (for the HUD). This is what makes "add a chord that arpeggiates,
  // then one that sustains" actually shape full-progression playback, not just
  // each chord's standalone preview tap.
  const buildProgrammedSteps = () => {
    const steps = [];
    blocks.forEach((block, i) => {
      const seg = segments[i];
      if (!seg) return;
      if (block.kind === "group") {
        const groupChords = (seg.type === "group" && seg.chords) || [];
        const groupReps = block.rep || 1;
        for (let r = 0; r < groupReps; r++) {
          block.chords.forEach((c, j) => {
            const parsedChord = groupChords[j];
            if (!parsedChord || c.kind !== "chord") return;
            const mode = modeById[c.id] || "strike";
            const innerReps = c.rep || 1;
            for (let k = 0; k < innerReps; k++)
              steps.push({ notes: realizeChord(parsedChord), mode, label: parsedChord.label });
          });
        }
      } else if (block.kind === "chord") {
        const reps = block.rep || 1;
        const mode = modeById[block.id] || "strike";
        for (let r = 0; r < reps; r++) steps.push({ notes: realizeChord(seg), mode, label: seg.label });
      } else if (block.kind === "raw") {
        // No client-side structure for an unparsed token's internals — fall
        // back to the server's own reps/shape, strike mode only.
        const reps = seg.reps || 1;
        const parts = seg.type === "group" && seg.chords ? seg.chords : seg.type === "chord" ? [seg] : [];
        for (let r = 0; r < reps; r++) {
          parts.forEach((pc) => steps.push({ notes: realizeChord(pc), mode: "strike", label: pc.label }));
        }
      }
    });
    return steps;
  };

  // Driven by `blocks`/`segments` (via buildProgrammedSteps), not
  // `parsed.chords` directly — an empty `keys` string is a quirky special case
  // server-side (mg.key_roots("") returns a default 12-chord demo circle
  // rather than []), which would otherwise make an empty builder look like it
  // has something to play.
  const programmedSteps = buildProgrammedSteps();

  // Play (or restart) the whole progression. `loopFlag` decides whether it
  // repeats — passed explicitly so Live can start a loop before the `live`
  // state has committed.
  const play = (loopFlag) => {
    const steps = programmedSteps.slice(0, MAX_PLAYBACK_CHORDS);
    if (!steps.length) return;
    setActiveId(null);
    setPlaySteps(steps);
    setPlayPos(0);
    playProgression(steps, {
      instrumentId,
      bpm,
      loop: loopFlag,
      onStep: setPlayPos,
      onEnd: loopFlag ? undefined : clearHud,
    });
  };

  // Live mode: toggling it on immediately starts a continuous loop that
  // re-renders on every edit (see the reactivity effect below); toggling off
  // stops everything. This is the "play as I change and add things" flow.
  const toggleLive = () => {
    const next = !live;
    setLive(next);
    if (next) play(true);
    else stopEverything();
  };

  // While Live is on, any change to the progression, tempo, instrument, or a
  // chord's playback mode restarts the loop with the new settings — so adding
  // a chord or flipping a mode is heard right away, no manual Stop + Play.
  useEffect(() => {
    if (live) play(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parsed, bpm, instrumentId, modeById]);

  // Report playback + save state up so App can render the sticky HUD and keep
  // the sticky Save button's suggested title current.
  useEffect(() => {
    const playing = playPos >= 0;
    const step = playing ? playSteps[playPos] : null;
    onStatus({
      playing,
      label: step ? step.label : "",
      pos: playPos,
      total: playSteps.length,
      mode: step ? step.mode : "",
      stepCount: programmedSteps.length,
      summary: summarizeSegments(segments),
      // Compact per-block labels for the navigation chip strip (App renders it
      // and scrolls to `chord-card-<id>` on tap).
      blocks: blocks.map((b, i) => ({ id: b.id, label: segments[i] ? labelForSegment(segments[i]) : "…" })),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playPos, playSteps, programmedSteps.length, segments, blocks]);

  const truncated = programmedSteps.length > MAX_PLAYBACK_CHORDS;

  return (
    <div className="builder">
      <div className="builder-transport">
        <button className="transport-btn play" onClick={() => play(live)} disabled={!programmedSteps.length}>
          ▸ Play
        </button>
        <button className="transport-btn stop" onClick={stopEverything}>
          ■ Stop
        </button>
        <button
          className={"transport-btn transport-toggle" + (live ? " on" : "")}
          onClick={toggleLive}
          disabled={!programmedSteps.length && !live}
        >
          ● Live
        </button>
        <Stepper value={bpm} min={MIN_BPM} max={MAX_BPM} step={4} label="bpm" onChange={setBpm} />
        <select
          className="instrument-select"
          value={instrumentId}
          onChange={(e) => setInstrumentId(e.target.value)}
        >
          {INSTRUMENTS.map((inst) => (
            <option key={inst.id} value={inst.id}>
              {inst.label}
            </option>
          ))}
        </select>
      </div>

      {!parsed.ok && parsed.error && <div className="builder-err">⚠ {parsed.error}</div>}
      {truncated && (
        <div className="builder-note">
          Progression expands to {programmedSteps.length} chords — playback previews the first{" "}
          {MAX_PLAYBACK_CHORDS}.
        </div>
      )}

      <div className="builder-cards">
        {blocks.map((b, i) =>
          b.kind === "group" ? (
            <GroupCard
              key={b.id}
              anchorId={"chord-card-" + b.id}
              block={b}
              recipes={recipes}
              parsed={segments[i]}
              modeById={modeById}
              onModeChange={setMode}
              activeId={activeId}
              onStrikeChord={triggerChord}
              onCreateChord={createChordForGroup}
              makeRandomFields={randomizeChordFields}
              randomMode={randomMode}
              onRandomizeGroup={() => randomizeBlock(i)}
              onPreview={() => previewGroup(b, segments[i])}
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
              anchorId={"chord-card-" + b.id}
              block={b}
              recipes={recipes}
              parsed={segments[i]}
              mode={modeById[b.id] || "strike"}
              onModeChange={(m) => setMode(b.id, m)}
              active={activeId === b.id}
              onStrike={() => (b.kind === "raw" ? triggerRaw(segments[i]) : triggerChord(b, segments[i]))}
              onChange={(patch) => setBlock(i, patch)}
              onRandomize={() => randomizeBlock(i)}
              onRemove={() => removeBlock(i)}
              onMoveUp={() => moveBlock(i, -1)}
              onMoveDown={() => moveBlock(i, 1)}
              canMoveUp={i > 0}
              canMoveDown={i < blocks.length - 1}
            />
          )
        )}
      </div>

      {/* Primary add/randomize actions, pinned to the bottom of the viewport so
          growing the progression never means scrolling to find the buttons. */}
      <div className="builder-actions">
        <button className="action-btn" onClick={addChord}>
          + Chord
        </button>
        <button className="action-btn" onClick={addGroup}>
          + Group
        </button>
        <button
          className="action-btn dice"
          onClick={randomizeAll}
          disabled={!blocks.length}
          title="Randomize every chord"
          aria-label="Randomize every chord"
        >
          🎲
        </button>
      </div>
    </div>
  );
}
