// Music Generator PWA — runs the pure-Python engine in the browser via Pyodide.
// Generates MIDI client-side, plays it with <midi-player>, and lets you browse a
// demo gallery and save a small on-device library.

import { initBuilder, refreshBuilder, setDemoChords } from "./builder.js";
import { initInterrupterBuilder } from "./interrupter.js";

const $ = (id) => document.getElementById(id);
const status = (msg) => { $("status").textContent = msg; };
const fmtSecs = (s) => {
  s = +s;
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};

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

// Named groove/interrupter banks from library/percussion_library.json.
const PERC_MAIN_PRESETS = [
  "rock:4/4:med", "rock:4/4:fast", "rock:4/4:halftime", "blues:4/4:shuffle",
  "jazz:4/4:swing", "funk:4/4:med", "salsa:4/4:clave-3-2", "bossa:4/4:med",
  "afro:12/8:med", "metal:4/4:blast-lite", "jazz:5/4:takefive",
];
const PERC_INTR_BANKS = [
  "accents:4/4:openhat", "accents:4/4:cowbell", "accents:4/4:clap", "fills:4/4:tomrim",
  "rock:4/4:med", "funk:4/4:med", "jazz:4/4:swing", "salsa:4/4:clave-3-2",
];
const CHORD_FAMILIES = [
  "triads", "sevenths", "ninths", "extended-chords",
  "quartal", "sus", "add6", "lyd-dom", "chromatic-mediants",
];

let last = { args: null, name: "", bytes: null };  // most recent generation

// ---------- engine (runs in a Web Worker so long renders never freeze the UI) ----------
let worker = null;
let ready = false;
let jobId = 0;
const pending = new Map();

function boot() {
  worker = new Worker("./worker.js", { type: "module" });
  worker.onmessage = (ev) => {
    const m = ev.data;
    if (m.type === "status") { status(m.message); return; }
    if (m.type === "ready") {
      ready = true;
      $("go").disabled = false; $("go").textContent = "Generate";
      status("Ready — fully offline from here on.");
      return;
    }
    if (m.type === "fatal") { status("Failed to start: " + m.message); return; }
    const p = pending.get(m.id);
    if (!p) return;
    pending.delete(m.id);
    if (m.type === "result") p.resolve(m.bytes); else p.reject(new Error(m.message));
  };
  worker.onerror = (e) => status("Worker error: " + (e.message || e));
}

function generateInWorker(args) {
  return new Promise((resolve, reject) => {
    const id = ++jobId;
    pending.set(id, { resolve, reject });
    worker.postMessage({ type: "generate", id, args });
  });
}

function bytesToDataUri(bytes) {
  let b = "";
  for (let i = 0; i < bytes.length; i++) b += String.fromCharCode(bytes[i]);
  return "data:audio/midi;base64," + btoa(b);
}

async function runGenerate(args, name) {
  if (!ready) return;
  $("go").disabled = true;
  const t0 = performance.now();
  const elapsed = () => ((performance.now() - t0) / 1000).toFixed(1);
  status("Generating…");
  const timer = setInterval(() => status(`Generating… ${elapsed()}s`), 200);
  try {
    const bytes = await generateInWorker(args);
    clearInterval(timer);
    last = { args, name, bytes };
    const uri = bytesToDataUri(bytes);
    $("player").src = uri;
    $("download").href = URL.createObjectURL(new Blob([bytes], { type: "audio/midi" }));
    $("download").download = (name || "music").replace(/[^a-z0-9]+/gi, "_") + ".mid";
    $("now-name").textContent = name || "Untitled";
    $("output").hidden = false;
    $("save").disabled = false;
    $("output").scrollIntoView({ behavior: "smooth", block: "nearest" });
    status(`Done in ${elapsed()}s. Tap ▶ to play.`);
  } catch (e) {
    clearInterval(timer);
    status("Generation failed: " + (e.message || e));
  } finally {
    $("go").disabled = false;
  }
}

// ---------- Create form ----------
// ---------- toggle chips (chord families, interrupter banks) ----------
function makeChip(boxId, val, label) {
  const b = document.createElement("button");
  b.type = "button"; b.className = "chip"; b.dataset.val = val; b.textContent = label;
  b.onclick = () => b.classList.toggle("active");
  $(boxId).appendChild(b);
}
const chipValues = (id) => [...$(id).querySelectorAll(".chip.active")].map((b) => b.dataset.val);
const setChips = (id, vals) => {
  for (const b of $(id).querySelectorAll(".chip")) b.classList.toggle("active", vals.includes(b.dataset.val));
};

function toggleChordIntrCustom() {
  $("chord-intr-custom").hidden = $("chord-intr-preset").value !== "__custom";
}
function onChordIntrPreset() {
  const val = $("chord-intr-preset").value;
  if (val !== "__custom") $("chord-intr").value = val;           // "" = off
  // a pattern is silent unless the fill rate is above zero — nudge it up once.
  if (val && val !== "__custom" && +$("chord-fill-rate").value === 0) {
    $("chord-fill-rate").value = 50; $("chord-fill-val").textContent = 50;
  }
  toggleChordIntrCustom();
}
function applyChordIntr(val) {
  const sel = $("chord-intr-preset");
  const presets = [...sel.options].map((o) => o.value).filter((x) => x && x !== "__custom");
  $("chord-intr").value = val || "";
  sel.value = !val ? "" : (presets.includes(val) ? val : "__custom");
  toggleChordIntrCustom();
}
const syncBassUI = () => {
  $("bass-step-field").style.display = $("bass-style").value === "follow" ? "none" : "";
};

function initControls() {
  const mkSel = $("perc-main-key");
  for (const k of PERC_MAIN_PRESETS) {
    const o = document.createElement("option"); o.value = k; o.textContent = k; mkSel.appendChild(o);
  }
  mkSel.value = DRUMS_MAIN_KEY;
  for (const b of PERC_INTR_BANKS) makeChip("perc-intr-chips", b, b);
  for (const f of CHORD_FAMILIES) makeChip("chords-chips", f, f);
  setChips("chords-chips", ["triads"]);

  const link = (id, lab) => $(id).addEventListener("input", () => { $(lab).textContent = $(id).value; });
  link("perc-fill-rate", "perc-fill-val");
  link("chord-fill-rate", "chord-fill-val");
  link("cp-step", "cp-step-val");
  link("cp-susp", "cp-susp-val");
  link("cp-ant", "cp-ant-val");
  link("bass-step", "bass-step-val");

  $("chord-intr-preset").addEventListener("change", onChordIntrPreset);
  $("chord-intr").addEventListener("input", () => {
    const t = $("chord-intr").value.trim();
    const presets = [...$("chord-intr-preset").options].map((o) => o.value);
    if (t && !presets.includes(t)) $("chord-intr-preset").value = "__custom";
    toggleChordIntrCustom();
  });
  $("bass-style").addEventListener("change", syncBassUI);

  // any percussion authoring implies drums are on
  const enableDrums = () => { $("drums").checked = true; };
  for (const id of ["perc-main", "perc-intr"])
    $(id).addEventListener("input", () => { if ($(id).value.trim()) enableDrums(); });
  $("perc-intr-chips").addEventListener("click", () => {
    if (chipValues("perc-intr-chips").length) enableDrums();
  });
}

function buildArgs() {
  const mode = $("mode").value;
  const args = ["--bpm", String($("bpm").value), "--instrument", $("instrument").value];
  const v = (id) => $(id).value;
  // push a flag only when the control differs from the engine default (keeps arg
  // lists clean and lets demos/saved items round-trip without churn).
  const opt = (flag, val, def) => {
    if (val !== "" && val != null && String(val) !== String(def)) args.push(flag, String(val));
  };
  const pct = (flag, id, def) => {
    const p = (+v(id)) / 100;
    if (Math.abs(p - def) > 1e-9) args.push(flag, String(p));
  };

  if (mode === "ostinato" || mode === "complete") {
    const keys = $("keys").value.trim();
    if (!keys) throw new Error("Enter at least one chord token, e.g. C::maj7, G::13");
    args.push("--mode", mode, "--keys", keys, "--seconds", String($("seconds").value));

    // harmony
    opt("--chord-length", v("chord-length"), "e");
    opt("--voicing", v("voicing"), "satb");
    opt("--satb-style", v("satb-style"), "block");
    opt("--velocity-mode-chords", v("vel-chords"), "uniform");
    opt("--chords-order", v("chords-order"), "random");
    const fams = chipValues("chords-chips");
    if (fams.length && !(fams.length === 1 && fams[0] === "triads")) args.push("--chords", ...fams);
    if (v("satb-style") === "counterpoint") {
      opt("--counterpoint-step", v("cp-step"), 0.5);
      pct("--counterpoint-suspension-prob", "cp-susp", 0.3);
      pct("--counterpoint-anticipation-prob", "cp-ant", 0.25);
    }

    // bass
    opt("--bass-style", v("bass-style"), "follow");
    if (v("bass-style") !== "follow") opt("--bass-step", v("bass-step"), 0.5);

    // melody / lead
    const mel = v("melody").trim();
    if (mel) {
      args.push("--melody", mel);
      opt("--melody-relative", v("melody-relative"), "key");
      opt("--melody-octave", v("melody-octave"), 5);
      opt("--melody-transform", v("melody-transform"), "none");
    }

    // percussion
    if ($("drums").checked) {
      args.push("--perc-lib", PERC_LIB);
      const main = v("perc-main").trim();
      if (main) args.push("--perc-main", main);
      else args.push("--perc-main-key", v("perc-main-key"));
      const fills = v("perc-intr").trim();
      if (fills) args.push("--perc-interrupters", fills);
      const banks = chipValues("perc-intr-chips");
      if (banks.length) args.push("--perc-interrupter-keys", ...banks);
      pct("--perc-fill-rate", "perc-fill-rate", 0.20);
      opt("--velocity-mode-drums", v("vel-drums"), "uniform");
    }

    // chord interrupters
    const chordIntr = v("chord-intr").trim();
    if (chordIntr) {
      args.push("--chord-interrupters", chordIntr);
      pct("--chord-fill-rate", "chord-fill-rate", 0.0);
    }

    // general
    if (v("seed").trim() !== "") args.push("--seed", v("seed").trim());
    if (!$("split-stems").checked) args.push("--no-split-stems");

  } else if (mode.startsWith("process:")) {
    const cell = $("cell").value.trim();
    if (!cell) throw new Error("Enter a melodic cell, e.g. e1 e2 e3 e5 e7 e5 e3 e2");
    args.push("--process", mode.split(":")[1].trim(), "--process-cell", cell,
              "--seconds", String($("seconds").value),
              "--melody-key", $("melkey").value.trim() || "C", "--melody-mode", $("melmode").value);
    if (v("process-reps").trim() !== "") args.push("--process-reps", v("process-reps").trim());
    if (v("process-stages").trim() !== "") args.push("--process-stages", v("process-stages").trim());
  } else if (mode === "fugue") {
    args.push("--melody-key", $("melkey").value.trim() || "C", "--melody-mode", $("melmode").value);
    const s = $("subject").value.trim();
    if (s) args.push("--fugue", s); else args.push("--fugue");
    const cs = v("countersubject").trim();
    if (cs) args.push("--fugue-countersubject", cs);
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
  // Anything absent resets to the engine default so demos don't leak into each
  // other.
  const get = (flag) => { const i = args.indexOf(flag); return i >= 0 ? args[i + 1] : null; };
  const getMulti = (flag) => {
    const i = args.indexOf(flag);
    if (i < 0) return null;
    const out = [];
    for (let j = i + 1; j < args.length && !String(args[j]).startsWith("--"); j++) out.push(args[j]);
    return out;
  };
  const sel = (id, val) => { $(id).value = val; };
  const range = (id, lab, val) => { $(id).value = val; if (lab) $(lab).textContent = val; };
  const pctRange = (id, lab, val, def) => {
    const n = Math.round((val != null ? +val : def) * 100);
    $(id).value = n; if (lab) $(lab).textContent = n;
  };

  let mode = get("--mode");
  if (args.includes("--fugue")) mode = "fugue";
  else if (get("--process")) mode = "process: " + get("--process");
  if (mode) $("mode").value = mode;
  if (get("--keys")) $("keys").value = get("--keys");
  if (get("--instrument") && [...$("instrument").options].some(o => o.value === get("--instrument")))
    $("instrument").value = get("--instrument");
  if (get("--bpm")) { $("bpm").value = get("--bpm"); $("bpm-val").textContent = get("--bpm"); }
  if (get("--seconds")) { $("seconds").value = get("--seconds"); $("sec-val").textContent = fmtSecs(get("--seconds")); }

  // harmony
  sel("chord-length", get("--chord-length") || "e");
  sel("voicing", get("--voicing") || "satb");
  sel("satb-style", get("--satb-style") || "block");
  sel("vel-chords", get("--velocity-mode-chords") || "uniform");
  sel("chords-order", get("--chords-order") || "random");
  setChips("chords-chips", getMulti("--chords") || ["triads"]);
  range("cp-step", "cp-step-val", get("--counterpoint-step") || "0.5");
  pctRange("cp-susp", "cp-susp-val", get("--counterpoint-suspension-prob"), 0.3);
  pctRange("cp-ant", "cp-ant-val", get("--counterpoint-anticipation-prob"), 0.25);

  // bass
  sel("bass-style", get("--bass-style") || "follow");
  range("bass-step", "bass-step-val", get("--bass-step") || "0.5");

  // melody
  $("melody").value = get("--melody") || "";
  sel("melody-relative", get("--melody-relative") || "key");
  $("melody-octave").value = get("--melody-octave") || "5";
  sel("melody-transform", get("--melody-transform") || "none");

  // percussion
  $("drums").checked = ["--perc-main-key", "--perc-main", "--perc-interrupters", "--perc-interrupter-keys"]
    .some((f) => args.includes(f));
  const mk = get("--perc-main-key");
  $("perc-main-key").value = (mk && PERC_MAIN_PRESETS.includes(mk)) ? mk : DRUMS_MAIN_KEY;
  $("perc-main").value = get("--perc-main") || "";
  $("perc-intr").value = get("--perc-interrupters") || "";
  setChips("perc-intr-chips", getMulti("--perc-interrupter-keys") || []);
  pctRange("perc-fill-rate", "perc-fill-val", get("--perc-fill-rate"), 0.20);
  sel("vel-drums", get("--velocity-mode-drums") || "uniform");

  // chord interrupters
  applyChordIntr(get("--chord-interrupters"));
  pctRange("chord-fill-rate", "chord-fill-val", get("--chord-fill-rate"), 0.0);

  // process / fugue extras
  if (get("--process-cell")) $("cell").value = get("--process-cell");
  $("process-reps").value = get("--process-reps") || "";
  $("process-stages").value = get("--process-stages") || "";
  const fug = get("--fugue");
  if (fug && !String(fug).startsWith("--")) $("subject").value = fug;
  $("countersubject").value = get("--fugue-countersubject") || "";
  if (get("--melody-key")) $("melkey").value = get("--melody-key");
  if (get("--melody-mode")) $("melmode").value = get("--melody-mode");

  // general
  $("seed").value = get("--seed") || "";
  $("split-stems").checked = !args.includes("--no-split-stems");

  syncModeUI();
  refreshBuilder();   // reflect the new keys into the chip strip
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
  // feed chord-mode demos to the builder's "Insert progression" picker
  const demoChords = EXAMPLES
    .filter(e => { const i = e.args.indexOf("--keys"); return i >= 0; })
    .map(e => ({ name: e.name, keys: e.args[e.args.indexOf("--keys") + 1] }));
  setDemoChords(demoChords);
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
  for (const id of ["perc-adv", "adv-harmony", "adv-bass", "adv-melody", "adv-chordintr"])
    $(id).style.display = chordMode ? "" : "none";
  $("advanced").style.display = chordMode ? "none" : "";
  $("advanced").open = !chordMode;
  syncBassUI();
}

document.querySelectorAll(".tab").forEach(t => t.onclick = () => showPanel(t.dataset.panel));
$("bpm").addEventListener("input", () => { $("bpm-val").textContent = $("bpm").value; });
$("seconds").addEventListener("input", () => { $("sec-val").textContent = fmtSecs($("seconds").value); });
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
initControls();
initInterrupterBuilder();
initBuilder({ keysInput: $("keys"), strip: $("chip-strip"), addBtn: $("add-chord"), insertBtn: $("insert-prog") });
$("copy-tokens").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("keys").value); status("Tokens copied."); }
  catch { status("Copy failed — select the field and copy manually."); }
});
renderExamples();
renderLibrary();
refreshCount();
syncModeUI();
boot();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("./sw.js").catch(() => {}));
}
