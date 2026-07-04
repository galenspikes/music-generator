// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// https://github.com/galenspikes/music-generator
import React, { useEffect, useMemo, useState } from "react";
import { marked } from "marked";

// The full docs/ Diátaxis tree rendered in-app (grouped sidebar: Tutorials,
// How-to, Reference, Explanation, …), plus the chord-recipe catalog as an
// interactive browser instead of a static table — click a recipe to insert it
// into the current progression.
export default function Docs({ spec, setField, setTab }) {
  const [sections, setSections] = useState([]);
  const [slug, setSlug] = useState("recipes");
  const [content, setContent] = useState("");
  const [recipes, setRecipes] = useState([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch("/api/docs").then((r) => r.json()).then((d) => setSections(d.sections || [])).catch(() => {});
    fetch("/api/recipes").then((r) => r.json()).then((d) => setRecipes(d.recipes || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (slug === "recipes") return;
    fetch(`/api/docs/${slug}`)
      .then((r) => r.json())
      .then((d) => setContent(d.content || ""))
      .catch(() => setContent("*failed to load*"));
  }, [slug]);

  const html = useMemo(
    () => (slug !== "recipes" ? marked.parse(content) : ""),
    [content, slug]
  );

  const allSlugs = useMemo(
    () => new Set(sections.flatMap((s) => s.docs.map((d) => d.slug))),
    [sections]
  );

  // Cross-links between docs (relative .md links, possibly with ../ or a
  // subdir) resolve against the current doc's directory and switch the in-app
  // doc instead of navigating away — as long as they land on a known slug.
  const handleDocClick = (e) => {
    const a = e.target.closest("a");
    if (!a) return;
    const href = a.getAttribute("href") || "";
    if (!/\.md($|[?#])/.test(href) || /^https?:\/\//.test(href)) return;
    const clean = href.replace(/[?#].*$/, "").replace(/\.md$/, "");
    // Resolve `clean` relative to the current slug's directory.
    const baseParts = slug.split("/").slice(0, -1);
    for (const part of clean.split("/")) {
      if (part === "." || part === "") continue;
      if (part === "..") baseParts.pop();
      else baseParts.push(part);
    }
    const target = baseParts.join("/");
    if (allSlugs.has(target)) {
      e.preventDefault();
      setSlug(target);
    }
  };

  const grouped = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = q
      ? recipes.filter(
          (r) =>
            r.name.toLowerCase().includes(q) ||
            r.description.toLowerCase().includes(q) ||
            r.category.toLowerCase().includes(q)
        )
      : recipes;
    const by = {};
    for (const r of filtered) (by[r.category] ||= []).push(r);
    return Object.entries(by);
  }, [recipes, search]);

  const insertRecipe = (name) => {
    const cur = (spec.keys || "").trim();
    const token = `C::${name}`;
    setField("keys")(cur ? `${cur}, ${token}` : token);
    setTab("editor");
  };

  return (
    <section className="docs-page">
      <nav className="docs-nav">
        <button className={"docs-navitem" + (slug === "recipes" ? " on" : "")}
          onClick={() => setSlug("recipes")}>◆ Chord Recipes</button>
        {sections.map((s) => (
          <div className="docs-navsection" key={s.section}>
            <div className="docs-navsection-label">{s.section}</div>
            {s.docs.map((d) => (
              <button key={d.slug} className={"docs-navitem" + (slug === d.slug ? " on" : "")}
                onClick={() => setSlug(d.slug)}>{d.title}</button>
            ))}
          </div>
        ))}
      </nav>
      <div className="docs-body">
        {slug === "recipes" ? (
          <div className="recipes-browser">
            <input
              className="textfield mono recipes-search"
              placeholder="search recipes…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <a className="recipes-deeplink" href="https://galenspikes.github.io/music-generator/chords.html"
              target="_blank" rel="noreferrer">
              Full pitch-class analysis — notes, prime form, Forte number, consonance ↗
            </a>
            {grouped.map(([cat, items]) => (
              <div className="recipes-group" key={cat}>
                <div className="recipes-group-label">{cat}</div>
                <div className="recipes-grid">
                  {items.map((r) => (
                    <div className="recipe-card" key={r.name}>
                      <div className="recipe-card-head">
                        <code className="recipe-name">{r.name}</code>
                        <button className="recipe-insert" onClick={() => insertRecipe(r.name)}>+ insert</button>
                      </div>
                      {r.description && <div className="recipe-desc">{r.description}</div>}
                      <div className="recipe-meta">
                        <span className="recipe-intervals">{r.intervals.join(", ")}</span>
                        <span className="recipe-notes">{r.notes.join(" ")}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
            {recipes.length > 0 && grouped.length === 0 && (
              <div className="recipes-empty">no recipes match "{search}"</div>
            )}
          </div>
        ) : (
          <div className="doc-md" onClick={handleDocClick} dangerouslySetInnerHTML={{ __html: html }} />
        )}
      </div>
    </section>
  );
}
