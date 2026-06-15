// Visual chord-token builder (Phase 1). A chip strip that is bidirectional with
// the tokens text field: tap a chip to edit (root/quality/inversion/bass/repeat)
// in a bottom sheet, drag to reorder, add/duplicate/delete. The tokens field
// stays the source of truth, so copy/paste round-trips with the engine.

const ROOTS = ["C","Db","D","Eb","E","F","Gb","G","Ab","A","Bb","B"];
const SHARP2FLAT = { "C#":"Db","D#":"Eb","F#":"Gb","G#":"Ab","A#":"Bb","E#":"F","B#":"C","Cb":"B","Fb":"E" };
const isNote = (s) => /^[A-G](b|#)?$/.test(s);
const norm = (r) => SHARP2FLAT[r] || r;

let chips = [];
let recipeGroups = [{ label: "Common", recipes: ["maj","min","maj7","min7","7","maj9","min9","13","sus4","quartal"] }];
let keysInput, strip, sheet, onChange, editing = -1;

// ---------- parse / serialize ----------
function splitTop(s) {
  const out = []; let depth = 0, cur = "";
  for (const ch of s) {
    if (ch === "[") depth++; if (ch === "]") depth--;
    if (ch === "," && depth === 0) { out.push(cur); cur = ""; } else cur += ch;
  }
  out.push(cur);
  return out.map((x) => x.trim()).filter(Boolean);
}

function parseTok(tok) {
  tok = tok.trim();
  let repeat = 1;
  const m = tok.match(/\*(\d+)$/);
  if (m) { repeat = +m[1]; tok = tok.slice(0, m.index); }
  if (tok.startsWith("[")) return { raw: tok + (repeat > 1 ? `*${repeat}` : "") };
  if (!tok.includes(":")) {
    let root = tok, recipe = "";
    if (/min$/i.test(root) && root.length > 3) { root = root.slice(0, -3); recipe = "min"; }
    else if (/m$/.test(root) && !isNote(root)) { root = root.slice(0, -1); recipe = "min"; }
    return { root: norm(root) || "C", inv: "", recipe, bass: "", repeat };
  }
  let bass = "";
  const bi = tok.indexOf("/");
  if (bi >= 0) { bass = tok.slice(bi + 1).trim(); tok = tok.slice(0, bi); }
  const parts = tok.split(":");
  let root = (parts[0] || "C").trim(), inv = (parts[1] || "").trim(), recipe = (parts[2] || "").trim();
  if (/m$/.test(root) && !isNote(root)) { root = root.slice(0, -1); if (!recipe) recipe = "min"; }
  return { root: norm(root), inv, recipe, bass: norm(bass), repeat };
}

function serTok(c) {
  if (c.raw !== undefined) return c.raw;
  let s = c.root;
  if (c.inv || c.recipe || c.bass) {
    const rec = c.recipe || (c.bass ? "maj" : "");
    s += (c.inv ? `:${c.inv}:` : "::") + rec + (c.bass ? `/${c.bass}` : "");
  }
  if (c.repeat && c.repeat > 1) s += `*${c.repeat}`;
  return s;
}

const serialize = () => chips.map(serTok).join(", ");

// ---------- progressions / chaining ----------
const SNIP_KEY = "musicgen.snippets.v1";
let demoChords = [];   // chord-mode demos, set from app.js

const PROGRESSIONS = [
  ["ii–V–I (C)", "D::min7, G::7, C::maj7"],
  ["I–V–vi–IV (C)", "C::maj, G::maj, A::min, F::maj"],
  ["vi–IV–I–V (C)", "A::min, F::maj, C::maj, G::maj"],
  ["I–vi–IV–V · 50s (C)", "C::maj, A::min, F::maj, G::maj"],
  ["Jazz turnaround (C)", "C::maj7, A::7, D::min7, G::7"],
  ["Minor ii–V–i (Am)", "B::m7b5, E::7b9, A::min9"],
  ["12-bar blues (C)", "C::7, C::7, C::7, C::7, F::7, F::7, C::7, C::7, G::7, F::7, C::7, G::7"],
  ["Rhythm changes A (Bb)", "Bb::maj7, G::min7, C::min7, F::7"],
  ["Andalusian cadence (Am)", "A::min, G::maj, F::maj, E::maj"],
  ["Circle of fifths", "C::maj7, F::maj7, B::m7b5, E::min7, A::min7, D::min7, G::7, C::maj7"],
  ["Pachelbel (D)", "D::maj, A::maj, B::min, Gb::min, G::maj, D::maj, G::maj, A::maj"],
  ["Coltrane / Giant Steps", "B::maj7, D::7, G::maj7, Bb::7, Eb::maj7"],
  ["Dorian vamp (Dm)", "D::min11*4, G::13*4"],
  ["Pop-punk (E)", "E::maj, B::maj, Db::min, A::maj"],
];

const loadSnips = () => { try { return JSON.parse(localStorage.getItem(SNIP_KEY)) || []; } catch { return []; } };
const saveSnips = (a) => localStorage.setItem(SNIP_KEY, JSON.stringify(a));

function appendKeys(keysStr) {
  const added = splitTop(keysStr).map(parseTok);
  if (!added.length) return;
  chips.push(...added);
  syncToText(); render();
}

function syncToText() {
  keysInput.value = serialize();
  if (onChange) onChange();
}

// ---------- chip label ----------
function chipLabel(c) {
  if (c.raw !== undefined) return c.raw;
  let s = c.root + (c.recipe ? " " + c.recipe : "");
  if (c.inv) s += " ·inv" + c.inv;
  if (c.bass) s += " /" + c.bass;
  if (c.repeat > 1) s += " ×" + c.repeat;
  return s;
}

// ---------- render strip ----------
function render() {
  strip.innerHTML = "";
  if (!chips.length) {
    const empty = document.createElement("span");
    empty.className = "chip-empty";
    empty.textContent = "No chords yet — tap ＋ Add chord or ⛓ Insert progression.";
    strip.appendChild(empty);
    return;
  }
  chips.forEach((c, i) => {
    const el = document.createElement("button");
    el.type = "button"; el.className = "chip-tok"; el.dataset.i = i;
    el.textContent = chipLabel(c);
    el.addEventListener("click", () => openSheet(i));
    strip.appendChild(el);
  });
}

// ---------- bottom sheet editor ----------
function fillSelect(sel, values, current, labelFn) {
  sel.innerHTML = "";
  for (const v of values) {
    const o = document.createElement("option");
    if (typeof v === "object") { o.value = v.value; o.textContent = v.label; }
    else { o.value = v; o.textContent = labelFn ? labelFn(v) : v; }
    sel.appendChild(o);
  }
  sel.value = current;
}

function openSheet(i) {
  editing = i;
  const c = chips[i];
  if (c.raw !== undefined) { // group/raw token: edit as text only
    const t = prompt("Edit token group:", c.raw);
    if (t !== null) { chips[i] = parseTok(t); syncToText(); render(); }
    return;
  }
  fillSelect(sheet.root, ROOTS, c.root);
  // quality select with optgroups
  sheet.recipe.innerHTML = "";
  const none = document.createElement("option");
  none.value = ""; none.textContent = "(default — from chord family)";
  sheet.recipe.appendChild(none);
  for (const g of recipeGroups) {
    const og = document.createElement("optgroup"); og.label = g.label;
    for (const r of g.recipes) {
      const o = document.createElement("option"); o.value = r; o.textContent = r;
      og.appendChild(o);
    }
    sheet.recipe.appendChild(og);
  }
  sheet.recipe.value = c.recipe || "";
  fillSelect(sheet.inv, [{ value: "", label: "root position" }, "1", "2", "3", "4", "5"], c.inv);
  fillSelect(sheet.bass, [{ value: "", label: "none" }, ...ROOTS], c.bass);
  sheet.rep.textContent = String(c.repeat || 1);
  sheet.el.hidden = false;
}

function readSheet() {
  if (editing < 0) return;
  chips[editing] = {
    root: sheet.root.value,
    recipe: sheet.recipe.value,
    inv: sheet.inv.value,
    bass: sheet.bass.value,
    repeat: Math.max(1, parseInt(sheet.rep.textContent, 10) || 1),
  };
  syncToText(); render();
}

function closeSheet() { sheet.el.hidden = true; editing = -1; }

// ---------- insert-progression sheet ----------
function snipRow(list, label, keys, onDelete) {
  const row = document.createElement("div"); row.className = "snip-row";
  const b = document.createElement("button"); b.className = "snip-add";
  b.innerHTML = `<b></b><small></small>`;
  b.querySelector("b").textContent = label;
  b.querySelector("small").textContent = keys;
  b.onclick = () => { appendKeys(keys); document.getElementById("snip").hidden = true; };
  row.appendChild(b);
  if (onDelete) {
    const d = document.createElement("button"); d.className = "ghost danger"; d.textContent = "✕";
    d.onclick = onDelete; row.appendChild(d);
  }
  list.appendChild(row);
}

function openSnips() {
  const list = document.getElementById("snip-list");
  list.innerHTML = "";
  const head = (t) => { const h = document.createElement("h3"); h.className = "cat"; h.textContent = t; list.appendChild(h); };
  head("Common progressions");
  for (const [name, keys] of PROGRESSIONS) snipRow(list, name, keys);
  const saved = loadSnips();
  if (saved.length) {
    head("Your saved progressions");
    saved.forEach((s, idx) => snipRow(list, s.name, s.keys, () => {
      const a = loadSnips(); a.splice(idx, 1); saveSnips(a); openSnips();
    }));
  }
  if (demoChords.length) {
    head("From demos");
    for (const d of demoChords) snipRow(list, d.name, d.keys);
  }
  document.getElementById("snip").hidden = false;
}

// ---------- public ----------
export function setDemoChords(list) { demoChords = list || []; }

export function refreshBuilder() {
  chips = splitTop(keysInput.value).map(parseTok);
  render();
}

export async function initBuilder(opts) {
  keysInput = opts.keysInput;
  strip = opts.strip;
  onChange = opts.onChange;
  sheet = {
    el: document.getElementById("sheet"),
    root: document.getElementById("f-root"),
    recipe: document.getElementById("f-recipe"),
    inv: document.getElementById("f-inv"),
    bass: document.getElementById("f-bass"),
    rep: document.getElementById("f-rep"),
  };
  try { recipeGroups = await (await fetch("./recipes.json")).json(); } catch {}

  opts.addBtn.onclick = () => {
    chips.push({ root: "C", recipe: "maj7", inv: "", bass: "", repeat: 1 });
    syncToText(); render(); openSheet(chips.length - 1);
  };
  keysInput.addEventListener("input", refreshBuilder);

  for (const id of ["root", "recipe", "inv", "bass"])
    sheet[id].addEventListener("change", readSheet);
  document.getElementById("f-rep-").onclick = () => { sheet.rep.textContent = Math.max(1, (+sheet.rep.textContent) - 1); readSheet(); };
  document.getElementById("f-rep+").onclick = () => { sheet.rep.textContent = Math.min(64, (+sheet.rep.textContent) + 1); readSheet(); };
  document.getElementById("f-move-").onclick = () => moveEditing(-1);
  document.getElementById("f-move+").onclick = () => moveEditing(1);
  document.getElementById("f-dup").onclick = () => {
    if (editing < 0) return;
    chips.splice(editing + 1, 0, { ...chips[editing] }); editing++;
    syncToText(); render();
  };
  document.getElementById("f-del").onclick = () => {
    if (editing < 0) return;
    chips.splice(editing, 1); syncToText(); render(); closeSheet();
  };
  document.getElementById("sheet-done").onclick = closeSheet;
  sheet.el.addEventListener("click", (e) => { if (e.target === sheet.el) closeSheet(); });

  // insert-progression / chaining
  opts.insertBtn.onclick = openSnips;
  document.getElementById("snip-done").onclick = () => { document.getElementById("snip").hidden = true; };
  document.getElementById("snip").addEventListener("click", (e) => {
    if (e.target.id === "snip") e.currentTarget.hidden = true;
  });
  document.getElementById("snip-save").onclick = () => {
    const keys = serialize();
    if (!keys.trim()) return;
    const name = prompt("Name this progression:", "My progression");
    if (!name) return;
    const a = loadSnips(); a.unshift({ name, keys }); saveSnips(a.slice(0, 30));
    document.getElementById("snip-save").textContent = "★ Saved!";
    setTimeout(() => { document.getElementById("snip-save").textContent = "★ Save current as progression…"; }, 1200);
  };

  refreshBuilder();
}

function moveEditing(dir) {
  const j = editing + dir;
  if (editing < 0 || j < 0 || j >= chips.length) return;
  const [m] = chips.splice(editing, 1);
  chips.splice(j, 0, m); editing = j;
  syncToText(); render();
}
