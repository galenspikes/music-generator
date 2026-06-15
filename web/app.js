// Music Generator PWA — runs the pure-Python engine in the browser via Pyodide.
// Generates MIDI client-side, plays it with <midi-player>, and lets you browse a
// demo gallery and save a small on-device library.

import { loadPyodide } from "./pyodide/pyodide.mjs";

const $ = (id) => document.getElementById(id);
const status = (msg) => { $("status").textContent = msg; };

const LIB_KEY = "musicgen.library.v1";
const LIB_MAX = 10;

const INSTRUMENTS = [
  ["Electric Piano", "epiano"], ["Piano", "piano"], ["Organ", "organ"],
  ["Nylon Guitar", "nylongt"], ["Jazz Guitar", "jazzguitar"], ["Dist. Guitar", "distguitar"],
  ["Clavinet", "clav"], ["Strings", "strings"], ["Warm Pad", "pad"], ["Choir", "choir"],
  ["Flute", "flute"], ["Saxophone", "sax"], ["Trumpet", "trumpet"],
  ["Vibraphone", "vibes"], ["Marimba", "marimba"], ["Harpsichord", "harpsi"], ["Synth Lead", "lead"],
];
const DRUMS_MAIN_KEY = "rock:4/4:med";
const PERC_LIB = "/engine/library/percussion_library.json";

let py = null;
let last = { args: null, name: "", bytes: null };  // most recent generation

// ---------- engine ----------
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
    return open(mg.main(), "rb").read()
`);
  $("go").disabled = false;
  $("go").textContent = "Generate";
  status("Ready — fully offline from here on.");
}

function bytesToDataUri(bytes) {
  let b = "";
  for (let i = 0; i < bytes.length; i++) b += String.fromCharCode(bytes[i]);
  return "data:audio/midi;base64," + btoa(b);
}

async function runGenerate(args, name) {
  if (!py) return;
  $("go").disabled = true;
  status("Generating…");
  try {
    const gen = py.globals.get("generate");
    const result = gen(py.toPy(args));
    const bytes = result.toJs();
    result.destroy(); gen.destroy();

    last = { args, name, bytes };
    const uri = bytesToDataUri(bytes);
    $("player").src = uri;
    $("download").href = URL.createObjectURL(new Blob([bytes], { type: "audio/midi" }));
    $("download").download = (name || "music").replace(/[^a-z0-9]+/gi, "_") + ".mid";
    $("now-name").textContent = name || "Untitled";
    $("output").hidden = false;
    $("save").disabled = false;
    $("output").scrollIntoView({ behavior: "smooth", block: "nearest" });
    status("Done. Tap ▶ to play.");
  } catch (e) {
    status("Generation failed: " + (e.message || e));
  } finally {
    $("go").disabled = false;
  }
}

// ---------- Create form ----------
function buildArgs() {
  const mode = $("mode").value;
  const args = ["--bpm", String($("bpm").value), "--instrument", $("instrument").value];
  if (mode === "ostinato" || mode === "complete") {
    const keys = $("keys").value.trim();
    if (!keys) throw new Error("Enter at least one chord token, e.g. C::maj7, G::13");
    args.push("--mode", mode, "--keys", keys, "--seconds", String($("seconds").value));
    if ($("drums").checked) args.push("--perc-lib", PERC_LIB, "--perc-main-key", DRUMS_MAIN_KEY);
  } else if (mode.startsWith("process:")) {
    const cell = $("cell").value.trim();
    if (!cell) throw new Error("Enter a melodic cell, e.g. e1 e2 e3 e5 e7 e5 e3 e2");
    args.push("--process", mode.split(":")[1].trim(), "--process-cell", cell,
              "--melody-key", $("melkey").value.trim() || "C", "--melody-mode", $("melmode").value);
  } else if (mode === "fugue") {
    args.push("--melody-key", $("melkey").value.trim() || "C", "--melody-mode", $("melmode").value);
    const s = $("subject").value.trim();
    if (s) args.push("--fugue", s); else args.push("--fugue");
  }
  return args;
}

function nameFromArgs() {
  const m = $("mode").value;
  if (m === "fugue") return "Fugue in " + $("melkey").value + " " + $("melmode").value;
  if (m.startsWith("process:")) return "Process · " + m.split(":")[1].trim();
  return ($("keys").value.split(",")[0] || "Custom").trim() + " …";
}

function applyArgs(args) {
  // Best-effort: reflect a saved/example arg list back into the form controls.
  const get = (flag) => { const i = args.indexOf(flag); return i >= 0 ? args[i + 1] : null; };
  let mode = get("--mode");
  if (args.includes("--fugue")) mode = "fugue";
  else if (get("--process")) mode = "process: " + get("--process");
  if (mode) $("mode").value = mode;
  if (get("--keys")) $("keys").value = get("--keys");
  if (get("--instrument") && [...$("instrument").options].some(o => o.value === get("--instrument")))
    $("instrument").value = get("--instrument");
  if (get("--bpm")) { $("bpm").value = get("--bpm"); $("bpm-val").textContent = get("--bpm"); }
  if (get("--seconds")) { $("seconds").value = get("--seconds"); $("sec-val").textContent = get("--seconds"); }
  $("drums").checked = args.includes("--perc-main-key");
  if (get("--process-cell")) $("cell").value = get("--process-cell");
  if (get("--melody-key")) $("melkey").value = get("--melody-key");
  if (get("--melody-mode")) $("melmode").value = get("--melody-mode");
  syncModeUI();
}

// ---------- Library (localStorage, capped) ----------
const loadLib = () => { try { return JSON.parse(localStorage.getItem(LIB_KEY)) || []; } catch { return []; } };
const saveLib = (lib) => localStorage.setItem(LIB_KEY, JSON.stringify(lib));

function refreshCount() { $("lib-count").textContent = String(loadLib().length); }

function saveCurrent() {
  if (!last.bytes) return;
  const lib = loadLib();
  if (lib.length >= LIB_MAX) {
    status(`Library is full (${LIB_MAX}). Delete one to save another.`);
    showPanel("library");
    return;
  }
  lib.unshift({
    id: Date.now(), name: last.name || "Untitled", args: last.args,
    midi: bytesToDataUri(last.bytes), ts: new Date().toLocaleString(),
  });
  saveLib(lib); renderLibrary(); refreshCount();
  status("Saved to your library.");
}

function renderLibrary() {
  const lib = loadLib();
  const list = $("library-list");
  list.innerHTML = "";
  $("library-empty").hidden = lib.length > 0;
  for (const item of lib) {
    const row = document.createElement("div");
    row.className = "lib-item";
    row.innerHTML = `<div class="lib-meta"><b></b><small></small></div>
      <div class="lib-actions">
        <button class="ghost" data-act="play">▶ Play</button>
        <button class="ghost" data-act="edit">Edit</button>
        <button class="ghost danger" data-act="del">✕</button>
      </div>`;
    row.querySelector("b").textContent = item.name;
    row.querySelector("small").textContent = item.ts;
    row.querySelector('[data-act="play"]').onclick = () => {
      $("player").src = item.midi;
      $("download").href = item.midi;
      $("download").download = item.name.replace(/[^a-z0-9]+/gi, "_") + ".mid";
      $("now-name").textContent = item.name;
      $("save").disabled = true;        // already saved
      last = { args: item.args, name: item.name, bytes: null };
      $("output").hidden = false;
      $("output").scrollIntoView({ behavior: "smooth", block: "nearest" });
    };
    row.querySelector('[data-act="edit"]').onclick = () => { applyArgs(item.args); showPanel("create"); };
    row.querySelector('[data-act="del"]').onclick = () => {
      saveLib(loadLib().filter(x => x.id !== item.id)); renderLibrary(); refreshCount();
    };
    list.appendChild(row);
  }
}

// ---------- Examples gallery (search + category chips + random) ----------
let EXAMPLES = [];
let exCat = "All";

function exFiltered() {
  const q = ($("ex-search").value || "").trim().toLowerCase();
  return EXAMPLES.filter(ex =>
    (exCat === "All" || ex.cat === exCat) &&
    (!q || (ex.name + " " + ex.desc + " " + ex.cat).toLowerCase().includes(q)));
}

function drawExamples() {
  const grid = $("examples-grid");
  const items = exFiltered();
  $("ex-status").textContent = `${items.length} demo${items.length === 1 ? "" : "s"} — tap to generate & play.`;
  const byCat = {};
  for (const ex of items) (byCat[ex.cat] = byCat[ex.cat] || []).push(ex);
  grid.innerHTML = "";
  for (const cat of Object.keys(byCat)) {
    const h = document.createElement("h3"); h.className = "cat"; h.textContent = cat;
    grid.appendChild(h);
    for (const ex of byCat[cat]) {
      const card = document.createElement("button");
      card.className = "example";
      card.innerHTML = `<b></b><span></span>`;
      card.querySelector("b").textContent = ex.name;
      card.querySelector("span").textContent = ex.desc;
      card.onclick = () => { applyArgs(ex.args); runGenerate(ex.args, ex.name); };
      grid.appendChild(card);
    }
  }
}

function drawChips() {
  const cats = ["All", ...[...new Set(EXAMPLES.map(e => e.cat))]];
  const box = $("ex-chips");
  box.innerHTML = "";
  for (const c of cats) {
    const b = document.createElement("button");
    b.className = "chip" + (c === exCat ? " active" : "");
    b.textContent = c === "All" ? `All ${EXAMPLES.length}` : c;
    b.onclick = () => { exCat = c; drawChips(); drawExamples(); };
    box.appendChild(b);
  }
}

async function renderExamples() {
  try { EXAMPLES = await (await fetch("./examples.json")).json(); } catch { EXAMPLES = []; }
  $("ex-count").textContent = String(EXAMPLES.length);
  $("ex-search").addEventListener("input", drawExamples);
  $("ex-random").addEventListener("click", () => {
    const items = exFiltered();
    if (!items.length) return;
    const ex = items[Math.floor(Math.random() * items.length)];
    applyArgs(ex.args); runGenerate(ex.args, ex.name);
  });
  drawChips();
  drawExamples();
}

// ---------- nav + small UI ----------
function showPanel(name) {
  for (const p of ["create", "examples", "library"]) $("panel-" + p).hidden = (p !== name);
  for (const t of document.querySelectorAll(".tab")) t.classList.toggle("active", t.dataset.panel === name);
}
function syncModeUI() {
  const m = $("mode").value;
  const chordMode = (m === "ostinato" || m === "complete");
  $("keys-field").style.display = chordMode ? "" : "none";
  $("advanced").open = !chordMode;
}

document.querySelectorAll(".tab").forEach(t => t.onclick = () => showPanel(t.dataset.panel));
$("bpm").addEventListener("input", () => { $("bpm-val").textContent = $("bpm").value; });
$("seconds").addEventListener("input", () => { $("sec-val").textContent = $("seconds").value; });
$("mode").addEventListener("change", syncModeUI);
$("go").addEventListener("click", () => {
  let args; try { args = buildArgs(); } catch (e) { status(e.message); return; }
  runGenerate(args, nameFromArgs());
});
$("save").addEventListener("click", saveCurrent);

for (const [label, alias] of INSTRUMENTS) {
  const o = document.createElement("option");
  o.value = alias; o.textContent = label;
  $("instrument").appendChild(o);
}
renderExamples();
renderLibrary();
refreshCount();
syncModeUI();
boot().catch((e) => status("Failed to start: " + (e.message || e)));

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("./sw.js").catch(() => {}));
}
