// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// Tap-driven chord-quality picker: a chip that opens a searchable, categorized
// card list (same grouping as webapp/frontend/src/Docs.jsx's recipe browser),
// fed by /api/recipes. Replaces a flat <select> with something that reads
// like flipping through a synth's patch bank.
import React, { useMemo, useState } from "react";
import Sheet from "./Sheet.jsx";
import { BARE } from "./tokenFormat.js";

export default function RecipePicker({ value, recipes, onChange }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const grouped = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = q
      ? recipes.filter(
          (r) =>
            r.name.toLowerCase().includes(q) ||
            (r.description || "").toLowerCase().includes(q) ||
            (r.category || "").toLowerCase().includes(q)
        )
      : recipes;
    const by = {};
    for (const r of filtered) (by[r.category || "Other"] ||= []).push(r);
    return Object.entries(by);
  }, [recipes, search]);

  const choose = (name) => {
    onChange(name);
    setOpen(false);
    setSearch("");
  };

  return (
    <>
      <button className="chip chip-recipe" onClick={() => setOpen(true)}>
        <span className="chip-label">Quality</span>
        <span className="chip-value">{value}</span>
      </button>
      <Sheet open={open} onClose={() => setOpen(false)} title="Choose chord quality">
        <input
          className="recipe-search"
          type="search"
          placeholder="search…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button className={"picker-btn bare-btn" + (value === BARE ? " on" : "")} onClick={() => choose(BARE)}>
          {BARE} — quality from families
        </button>
        {grouped.map(([cat, items]) => (
          <div className="recipe-group" key={cat}>
            <div className="recipe-group-label">{cat}</div>
            <div className="recipe-cards">
              {items.map((r) => (
                <button
                  key={r.name}
                  className={"recipe-card-btn" + (value === r.name ? " on" : "")}
                  onClick={() => choose(r.name)}
                >
                  <code className="recipe-card-name">{r.name}</code>
                  {r.notes && <span className="recipe-card-notes">{r.notes.join(" ")}</span>}
                </button>
              ))}
            </div>
          </div>
        ))}
        {recipes.length > 0 && grouped.length === 0 && (
          <div className="recipe-empty">no qualities match "{search}"</div>
        )}
      </Sheet>
    </>
  );
}
