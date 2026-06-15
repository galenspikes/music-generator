// interrupter.js — a tap-to-build popup (bottom sheet) for percussion/chord
// interrupter motifs and grooves. Saves the user from typing token strings on
// mobile: pick a length, tap the hits, "Add step", repeat. Writes the assembled
// comma-separated token list back into a target text field.

const $ = (id) => document.getElementById(id);

const DURATIONS = [
  ["w", "whole"], ["h", "half"], ["q", "quarter"],
  ["e", "8th"], ["s", "16th"], ["t", "32nd"],
];
// Drum-letter map mirrors docs/token-grammar.md / percussion_library.json.
const DRUM_HITS = [
  ["b", "Kick"], ["c", "Snare"], ["e", "Side stick"], ["f", "Clap"],
  ["g", "Closed hat"], ["h", "Pedal hat"], ["i", "Open hat"], ["j", "Crash"],
  ["k", "Ride"], ["x", "Cowbell"], ["w", "Tambourine"], ["r", "Rest"],
];
const CHORD_HITS = [["c", "Chord"], ["r", "Rest"]];

let steps = [];               // [{ dur, letters: [..] }]
let curDur = "e";
let curLetters = new Set();
let targetId = null;          // input the result is written into
let hits = DRUM_HITS;

const tokenOf = (st) => st.dur + st.letters.join("");
const previewStr = () => steps.map(tokenOf).join(",");

function parse(str) {
  return (str || "").split(",").map((s) => s.trim()).filter(Boolean).map((tok) => ({
    dur: tok[0],
    letters: tok.slice(1).split(""),
  }));
}

function chipBtn(label, active, onClick) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "chip" + (active ? " active" : "");
  b.textContent = label;
  b.onclick = onClick;
  return b;
}

function render() {
  $("intr-preview").textContent = previewStr() || "—";

  const stepBox = $("intr-steps");
  stepBox.textContent = "";
  if (!steps.length) {
    const s = document.createElement("span");
    s.className = "chip-empty";
    s.textContent = "no steps yet";
    stepBox.appendChild(s);
  }
  steps.forEach((st, i) => {
    stepBox.appendChild(chipBtn(tokenOf(st) + " ✕", false, () => {
      steps.splice(i, 1); render();
    }));
  });

  const durBox = $("intr-durs");
  durBox.textContent = "";
  for (const [d, name] of DURATIONS) {
    durBox.appendChild(chipBtn(name, d === curDur, () => { curDur = d; render(); }));
  }

  const instBox = $("intr-insts");
  instBox.textContent = "";
  for (const [l, name] of hits) {
    instBox.appendChild(chipBtn(name, curLetters.has(l), () => {
      if (l === "r") { curLetters.clear(); curLetters.add("r"); }
      else { curLetters.delete("r"); curLetters.has(l) ? curLetters.delete(l) : curLetters.add(l); }
      render();
    }));
  }
}

function addStep() {
  if (!curLetters.size) return;                 // need at least one hit (or rest)
  steps.push({ dur: curDur, letters: [...curLetters] });
  curLetters.clear();
  render();
}

function close() { $("intr-sheet").hidden = true; targetId = null; }

function done() {
  if (targetId) {
    const el = $(targetId);
    el.value = previewStr();
    el.dispatchEvent(new Event("input", { bubbles: true }));
  }
  close();
}

// Open the builder targeting `inputId`. kind: "drum" | "chord".
export function openInterrupterBuilder(inputId, kind) {
  targetId = inputId;
  hits = kind === "chord" ? CHORD_HITS : DRUM_HITS;
  steps = parse($(inputId).value);
  curLetters = new Set();
  curDur = "e";
  $("intr-title").textContent = kind === "chord" ? "Build chord interrupter" : "Build pattern";
  $("intr-sheet").hidden = false;
  render();
}

export function initInterrupterBuilder() {
  $("intr-add").onclick = addStep;
  $("intr-clear").onclick = () => { steps = []; curLetters.clear(); render(); };
  $("intr-done").onclick = done;
  // tap the dimmed backdrop (the sheet itself, outside the card) to dismiss
  $("intr-sheet").addEventListener("click", (e) => {
    if (e.target.id === "intr-sheet") close();
  });

  const wire = (btnId, inputId, kind) => {
    const b = $(btnId);
    if (b) b.onclick = () => openInterrupterBuilder(inputId, kind);
  };
  wire("build-main", "perc-main", "drum");
  wire("build-perc-intr", "perc-intr", "drum");
  wire("build-chord-intr", "chord-intr", "chord");
}
