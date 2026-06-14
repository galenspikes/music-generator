// Music Generator PWA — runs the pure-Python engine in the browser via Pyodide.
// The engine generates a MIDI file in Pyodide's in-memory filesystem; we read
// the bytes back and hand them to <midi-player> for playback + download.

import { loadPyodide } from "./pyodide/pyodide.mjs";

const $ = (id) => document.getElementById(id);
const status = (msg) => { $("status").textContent = msg; };

const INSTRUMENTS = [
  ["Electric Piano", "epiano"], ["Piano", "piano"], ["Organ", "organ"],
  ["Nylon Guitar", "nylongt"], ["Jazz Guitar", "jazzguitar"], ["Strings", "strings"],
  ["Choir", "choir"], ["Flute", "flute"], ["Saxophone", "sax"], ["Trumpet", "trumpet"],
  ["Vibraphone", "vibes"], ["Marimba", "marimba"], ["Harpsichord", "harpsi"],
  ["Synth Lead", "lead"], ["Warm Pad", "pad"],
];

const CHORD_FAMILIES = ["triads", "sevenths", "ninths", "extended-chords",
  "quartal", "sus", "add6", "chromatic-mediants", "lyd-dom"];

let py = null;

function populateInstruments() {
  const sel = $("instrument");
  for (const [label, alias] of INSTRUMENTS) {
    const o = document.createElement("option");
    o.value = alias; o.textContent = label;
    sel.appendChild(o);
  }
}

function buildArgs() {
  const mode = $("mode").value;
  const bpm = String($("bpm").value);
  const instrument = $("instrument").value;
  const args = ["--bpm", bpm, "--instrument", instrument];

  if (mode === "ostinato" || mode === "complete") {
    const keys = $("keys").value.trim();
    if (!keys) throw new Error("Enter at least one chord token, e.g. C::maj7, G::13");
    args.push("--mode", mode, "--keys", keys, "--seconds", String($("seconds").value));
    if ($("drums").checked) {
      args.push("--perc-lib", "/engine/library/percussion_library.json",
                "--perc-main-key", "rock:4/4:med");
    }
  } else if (mode.startsWith("process:")) {
    const kind = mode.split(":")[1].trim();
    const cell = $("cell").value.trim();
    if (!cell) throw new Error("Enter a melodic cell, e.g. e1 e2 e3 e5 e7 e5 e3 e2");
    args.push("--process", kind, "--process-cell", cell,
              "--melody-key", $("melkey").value.trim() || "C",
              "--melody-mode", $("melmode").value);
  } else if (mode === "fugue") {
    args.push("--melody-key", $("melkey").value.trim() || "C",
              "--melody-mode", $("melmode").value);
    const subj = $("subject").value.trim();
    if (subj) args.push("--fugue", subj); else args.push("--fugue");
  }
  return args;
}

async function boot() {
  status("Loading Pyodide (Python → WebAssembly)…");
  py = await loadPyodide({ indexURL: "./pyodide/" });
  status("Loading numpy…");
  await py.loadPackage(["numpy", "pyyaml", "packaging"]);

  status("Loading the music engine…");
  const buf = await (await fetch("./engine.zip")).arrayBuffer();
  py.unpackArchive(buf, "zip", { extractDir: "/engine" });

  py.runPython(`
import sys, os
sys.path.insert(0, "/engine")
os.environ["MUSICGEN_OUTPUT_DIR"] = "/out"
import music_generator as mg

def generate(args):
    args = [str(a) for a in args]
    sys.argv = ["music_generator.py", *args, "--out", "web", "--no-play"]
    path = mg.main()
    return open(path, "rb").read()
`);

  $("go").disabled = false;
  $("go").textContent = "Generate";
  status("Ready — fully offline from here on.");
}

async function generate() {
  let args;
  try { args = buildArgs(); }
  catch (e) { status(e.message); return; }

  $("go").disabled = true;
  status("Generating…");
  try {
    const gen = py.globals.get("generate");
    const result = gen(py.toPy(args));      // Python bytes
    const bytes = result.toJs();            // Uint8Array
    result.destroy(); gen.destroy();

    const blob = new Blob([bytes], { type: "audio/midi" });
    const url = URL.createObjectURL(blob);
    let b64 = "";
    for (let i = 0; i < bytes.length; i++) b64 += String.fromCharCode(bytes[i]);
    $("player").src = "data:audio/midi;base64," + btoa(b64);
    $("download").href = url;
    $("output").hidden = false;
    status("Done. Tap ▶ to play, or download the MIDI.");
  } catch (e) {
    status("Generation failed: " + (e.message || e));
  } finally {
    $("go").disabled = false;
  }
}

// live slider labels
$("bpm").addEventListener("input", () => { $("bpm-val").textContent = $("bpm").value; });
$("seconds").addEventListener("input", () => { $("sec-val").textContent = $("seconds").value; });
$("mode").addEventListener("change", () => {
  const m = $("mode").value;
  const chordMode = (m === "ostinato" || m === "complete");
  $("keys-field").style.display = chordMode ? "" : "none";
  if (!chordMode) $("advanced").open = true;
});
$("go").addEventListener("click", generate);

populateInstruments();
boot().catch((e) => status("Failed to start: " + (e.message || e)));

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () =>
    navigator.serviceWorker.register("./sw.js").catch(() => {}));
}
