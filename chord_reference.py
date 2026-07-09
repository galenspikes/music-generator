# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""Generate the chord-recipe reference: an interactive explorer and a docs table.

Reads ``library/chord_recipes.py`` (names, offsets, category groupings, per-entry
glosses), analyses every recipe with :mod:`theory`, attaches curated notes with
citations for the iconic sonorities, and writes:

  * ``site/chords.html``            — self-contained interactive explorer
  * ``docs/reference/chord-recipes.md`` — a footnoted reference table
  * ``<scratchpad>/chords-artifact.html`` (only with --artifact) — a body-only
    build for publishing as a shareable Artifact.

Run ``python chord_reference.py`` (or ``make chords``). Theory sources are
footnoted; see REFERENCES.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

import theory

REPO = Path(__file__).resolve().parent
RECIPES_SRC = REPO / "library" / "chord_recipes.py"


# --- bibliography -------------------------------------------------------------
# (key, short-mark, full citation). Order fixes the footnote numbers.
REFERENCES: list[tuple[str, str]] = [
    ("forte",
     "Allen Forte, <em>The Structure of Atonal Music</em> "
     "(New Haven: Yale University Press, 1973). Source of the set-class names "
     "(&ldquo;Forte numbers&rdquo;) and the interval-class vector."),
    ("rahn",
     "John Rahn, <em>Basic Atonal Theory</em> (New York: Longman, 1980). "
     "Prime form by the &ldquo;most packed to the left&rdquo; selection used here."),
    ("straus",
     "Joseph N. Straus, <em>Introduction to Post-Tonal Theory</em>, 4th ed. "
     "(New York: W. W. Norton, 2016). Normal-form / prime-form procedure."),
    ("huron",
     "David Huron, &ldquo;Interval-Class Content in Equally Tempered "
     "Pitch-Class Sets: Common Scales Exhibit Optimum Tonal Consonance,&rdquo; "
     "<em>Music Perception</em> 11/3 (1994): 289&ndash;305. The aggregate "
     "dyadic consonance measure used for the consonance/dissonance rating."),
    ("messiaen",
     "Olivier Messiaen, <em>Technique de mon langage musical</em> "
     "(Paris: Alphonse Leduc, 1944). Modes of limited transposition "
     "(whole-tone = mode 1; octatonic = mode 2)."),
    ("aldwell",
     "Edward Aldwell &amp; Carl Schachter, <em>Harmony and Voice Leading</em>, "
     "4th ed. (Boston: Schirmer, 2011). Augmented-sixth and Neapolitan chords."),
    ("persichetti",
     "Vincent Persichetti, <em>Twentieth-Century Harmony</em> "
     "(New York: W. W. Norton, 1961). Quartal / quintal harmony."),
    ("levine",
     "Mark Levine, <em>The Jazz Theory Book</em> (Petaluma: Sher Music, 1995). "
     "Altered dominants, upper-structure and quartal voicings."),
    ("wagner",
     "Richard Wagner, <em>Tristan und Isolde</em> (1865), opening measures."),
    ("scriabin",
     "Alexander Scriabin, <em>Prometheus: The Poem of Fire</em>, Op. 60 (1910)."),
    ("petrushka",
     "Igor Stravinsky, <em>Petrushka</em> (1911), second tableau."),
    ("rite",
     "Igor Stravinsky, <em>The Rite of Spring</em> (1913), "
     "&ldquo;Augurs of Spring.&rdquo;"),
    ("davis",
     "Miles Davis, &ldquo;So What,&rdquo; <em>Kind of Blue</em> (Columbia, 1959); "
     "quartal voicing by Bill Evans."),
]
REF_NUM = {key: i + 1 for i, (key, _) in enumerate(REFERENCES)}


def cite(*keys: str) -> str:
    """Superscript footnote marker(s) linking to the references list."""
    out = []
    for k in keys:
        n = REF_NUM[k]
        out.append(f'<sup class="fn"><a href="#ref-{n}" id="cite-{k}">{n}</a></sup>')
    return "".join(out)


# --- curated notes for the iconic sonorities (everything else auto-glosses) ---
CURATED: dict[str, str] = {
    "tristan": (
        "The opening sonority of Wagner&rsquo;s <em>Tristan und Isolde</em>"
        + cite("wagner") +
        " &mdash; enharmonically a half-diminished seventh (set class 4-27)"
        + cite("forte") +
        ", though its function is famously ambiguous. Its chromatic voice-leading "
        "pull, not its label, is the point."),
    "mystic": (
        "Scriabin&rsquo;s &ldquo;mystic&rdquo; (or &ldquo;Prometheus&rdquo;) "
        "chord" + cite("scriabin") +
        ", set class 6-34" + cite("forte") +
        " &mdash; built largely in fourths, transpositionally coloured and without "
        "a single tonal centre."),
    "petrushka": (
        "Two major triads a tritone apart (C + F&sharp;), the bitonal "
        "&ldquo;Petrushka chord&rdquo;" + cite("petrushka") + "."),
    "augurs": (
        "The pounding chord of the &ldquo;Augurs of Spring&rdquo; from "
        "<em>The Rite of Spring</em>" + cite("rite") +
        ": an E&flat; dominant seventh over an F&flat;-major triad, reduced here "
        "to its clashing core."),
    "whole_tone": (
        "A segment of the whole-tone scale &mdash; Messiaen&rsquo;s first mode of "
        "limited transposition" + cite("messiaen") +
        " (set class 6-35)" + cite("forte") +
        ", transpositionally symmetric and tonally weightless."),
    "messiaen_dom": (
        "A symmetric &ldquo;dominant&rdquo; colour after Messiaen"
        + cite("messiaen") +
        "; it shares its set class (6-34) with Scriabin&rsquo;s mystic chord."),
    "messiaen_resonance": (
        "Messiaen&rsquo;s resonance chord" + cite("messiaen") +
        " &mdash; overtones of a low fundamental, spelled before reduction mod 12."),
    "messiaen_resonance_pc": (
        "The resonance chord" + cite("messiaen") +
        " reduced to pitch classes (set class 7-34, the altered/acoustic family)."),
    "it6": ("Italian augmented sixth &mdash; a chromatic pre-dominant whose "
            "&sharp;6/&flat;6 frame resolves outward to the dominant." + cite("aldwell")),
    "fr6": ("French augmented sixth" + cite("aldwell") +
            " &mdash; a whole-tone tetrachord (set class 4-25) with two tritones."),
    "ger6": ("German augmented sixth" + cite("aldwell") +
             " &mdash; enharmonically a dominant seventh; an all-interval "
             "tetrachord (4-Z15)."),
    "n6": ("The Neapolitan (&flat;II), usually voiced in first inversion as a "
           "pre-dominant." + cite("aldwell")),
    "quartal": ("Quartal harmony &mdash; a chord built in fourths rather than "
                "thirds." + cite("persichetti")),
    "quartal7": ("Four stacked fourths." + cite("persichetti")),
    "so_what": ("The &ldquo;So What&rdquo; voicing &mdash; three fourths capped "
                "by a third, from <em>Kind of Blue</em>." + cite("davis", "persichetti")),
    "7alt": ("The altered dominant: a dominant seventh carrying every alteration "
             "(&flat;9, &sharp;9, &flat;5, &sharp;5), the upper structure of the "
             "altered (super-Locrian) scale, set class 7-34." + cite("levine")),
    "bartok": ("The diminished-seventh tetrachord &mdash; a symmetric slice of "
               "the octatonic collection (Messiaen&rsquo;s mode 2)." + cite("messiaen")),
    "octatonic_tet": ("A diminished-seventh cell of the octatonic collection "
                      "(Messiaen&rsquo;s mode 2)." + cite("messiaen")),
    "lydian_stack": ("A Lydian-flavoured major seventh (&sharp;11) voicing."),
    "maj7#11": ("The Lydian major-seventh (&sharp;11) colour of film and fusion "
                "harmony." + cite("levine")),
}


# Presentational grouping (curated names + order). Every recipe must appear in
# exactly one group; build_catalog() raises otherwise so a new recipe can't be
# silently dropped. Glosses still come from the source's per-entry comments.
CATEGORIES: list[tuple[str, list[str]]] = [
    ("Triads", ["maj", "min", "dim", "aug"]),
    ("Seventh chords",
     ["7", "maj7", "min7", "mmaj7", "hdim7", "m7b5", "wdim7", "dim7"]),
    ("Suspended", ["sus2", "sus4", "sus2add7", "sus4add7"]),
    ("Added-tone (major)",
     ["majadd6", "majadd9", "majaddb9", "majadd#9", "majadd11", "majadd#11",
      "majaddb13", "majadd13", "maj7add9"]),
    ("Added-tone (minor)", ["minadd6", "minadd9", "minadd11"]),
    ("Extended", ["9", "maj9", "min9", "11", "13", "min11", "min13"]),
    ("Altered dominants",
     ["7b5", "7#5", "7b9", "7#9", "7b11", "7#11", "7b13", "7#13", "7alt"]),
    ("Split third", ["split3", "maj7split3", "7split3"]),
    ("Power chords", ["5", "5add8", "5add9"]),
    ("Augmented sixths & Neapolitan", ["it6", "fr6", "ger6", "n6"]),
    ("Quartal & modern",
     ["quartal", "quartal7", "quintal", "so_what", "lydian_stack"]),
    ("Famous & iconic", ["tristan", "mystic", "whole_tone", "petrushka", "augurs"]),
    ("Messiaen-inspired",
     ["messiaen_resonance", "messiaen_resonance_pc", "messiaen_dom"]),
    ("Clusters & symmetry",
     ["tone_cluster_3", "tone_cluster_4", "tone_cluster_5", "chromatic_cluster",
      "diatonic_cluster", "bartok", "octatonic_tet", "wholetone_tet"]),
    ("Colours & utilities",
     ["add4", "sus2add6", "maj7#11", "min7#11", "min7add9", "lyd-dom"]),
]


_TENSIONS = ("♭9", "♯9", "♯11", "♭5", "♯5", "♭13")


def _join(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def describe(gloss: str, offsets: list[int], notes: list[dict],
             flags: list[str], con: dict) -> str:
    """Compose a plain-language description for any recipe from its analysis."""
    sents: list[str] = []
    base = gloss.strip()
    if base:
        base = html.escape(base[0].upper() + base[1:])
        sents.append(base if base.endswith(".") else base + ".")

    if "quartal / quintal" in flags:
        sents.append("It is built by stacking fourths rather than thirds.")
    elif "chromatic cluster" in flags:
        sents.append("It is a chromatic cluster of adjacent semitones.")
    elif len(offsets) > 2 and all(
            3 <= b - a <= 4 for a, b in zip(sorted(offsets), sorted(offsets)[1:])):
        sents.append("It stacks in thirds.")

    if "transpositionally symmetric" in flags:
        sents.append("It divides the octave evenly, so no single note is heard "
                     "as the root.")
    elif "inversionally symmetric" in flags:
        sents.append("It is symmetric under inversion.")

    seen: set[str] = set()
    tensions = [d for d in (n["degree"] for n in notes)
                if d in _TENSIONS and not (d in seen or seen.add(d))]
    if tensions:
        sents.append("Its colour comes from the " + _join(tensions) + ".")

    sents.append(f"Its dyads are {con['band']} &mdash; {con['reading']}.")
    return " ".join(sents)


def parse_glosses() -> dict[str, str]:
    """Per-entry gloss text from the trailing ``# comment`` on each recipe line."""
    glosses: dict[str, str] = {}
    entry_re = re.compile(r'^\s*"([^"]+)":\s*\[[^\]]*\]\s*,?\s*#\s*(.*)$')
    for line in RECIPES_SRC.read_text(encoding="utf-8").splitlines():
        m = entry_re.match(line)
        if m:
            glosses[m.group(1)] = m.group(2).strip()
    return glosses


def build_catalog() -> dict:
    """Analyse every chord recipe into the JSON-able catalog the reference
    page renders: per-recipe intervals, pitch-class set analysis
    (normal/prime form, Forte number, interval-class vector, consonance),
    category, and the hand-written gloss parsed from chord_recipes.py."""
    from chord_recipes import CHORD_RECIPES  # noqa: E402  (added to path in main)

    glosses = parse_glosses()
    cats = CATEGORIES
    cat_of = {name: title for title, names in cats for name in names}

    # completeness: every recipe filed exactly once; no phantom names
    known = set(CHORD_RECIPES)
    listed = [n for _, names in cats for n in names]
    missing = known - set(listed)
    phantom = [n for n in listed if n not in known]
    dupes = [n for n in listed if listed.count(n) > 1]
    if missing or phantom or dupes:
        raise SystemExit(
            f"category map out of sync — missing={sorted(missing)} "
            f"phantom={phantom} duplicated={sorted(set(dupes))}")

    # alias groups: recipes with identical offsets
    by_offsets: dict[tuple[int, ...], list[str]] = {}
    for name, offs in CHORD_RECIPES.items():
        by_offsets.setdefault(tuple(offs), []).append(name)

    recipes = {}
    for name, offs in CHORD_RECIPES.items():
        a = theory.analyze(offs)
        aliases = [n for n in by_offsets[tuple(offs)] if n != name]
        gloss = glosses.get(name, "")
        curated = CURATED.get(name, "")
        auto = describe(gloss, offs, a["notes"], a["flags"], a["consonance"])
        recipes[name] = {
            "name": name,
            "category": cat_of.get(name, ""),
            "offsets": a["offsets"],
            "notes": a["notes"],           # degree/step/name over C
            "prime": a["prime_str"],
            "forte": a["forte"] or "—",
            "icv": a["icv"],
            "intervals": a["intervals"],
            "flags": a["flags"],
            "consonance": a["consonance"],
            "gloss": gloss,
            "curated": curated,
            "description": auto + (" " + curated if curated else ""),
            "aliases": aliases,
        }
    order = [{"title": t, "names": ns} for t, ns in cats]
    return {"recipes": recipes, "categories": order,
            "huron_ref": REF_NUM["huron"]}


# --- rendering ----------------------------------------------------------------
def render_references_html() -> str:
    items = []
    for key, text in REFERENCES:
        n = REF_NUM[key]
        items.append(
            f'<li id="ref-{n}"><span class="ref-n">{n}.</span> {text} '
            f'<a class="ref-back" href="#cite-{key}" '
            f'aria-label="back to citation">&#8617;</a></li>')
    return "<ol class=\"refs\">" + "".join(items) + "</ol>"


def render_html(catalog: dict, *, full_document: bool) -> str:
    """Render the interactive chord-reference page (recipe rack, keyboard,
    Web-Audio preview) from :func:`build_catalog`'s output. With
    ``full_document`` emit a standalone HTML page; without, a fragment for
    embedding (the webapp's Docs tab)."""
    data_json = json.dumps(catalog, separators=(",", ":"))
    refs_html = render_references_html()
    intro = (
        "Every chord recipe in the generator, analysed. Pick one from the rack to "
        "light its notes on the keyboard, hear it (short, sustained, or "
        "arpeggiated), and read its pitch-class set &mdash; normal and prime "
        f"form{cite('rahn', 'straus')}, Forte number{cite('forte')}, "
        f"interval-class vector{cite('forte')}, and a consonance rating after "
        f"Huron{cite('huron')}.")
    body = f"""
  <nav class="chd-nav">
    <div class="wrap chd-nav-inner">
      <a class="chd-nav-brand" href="index.html">Music Generator</a>
      <ul class="chd-nav-links">
        <li><a href="index.html">Home</a></li>
        <li><a href="chords.html" aria-current="page">Chords</a></li>
        <li><a href="https://gsp87-music-generator.hf.space/chords/">ChordBuilder</a></li>
        <li><a href="https://galenspikes.github.io/music-generator/docs/">Docs</a></li>
        <li><a href="https://github.com/galenspikes/music-generator">GitHub</a></li>
        <li><a class="chd-nav-cta" href="https://huggingface.co/spaces/gsp87/music-generator">Player &rarr;</a></li>
      </ul>
    </div>
  </nav>

  <header class="rack-head">
    <div class="wrap head-inner">
      <div class="brand-plate">
        <div class="brand-name">CHORD&nbsp;RECIPES</div>
        <div class="brand-sub">pitch-class set analyser</div>
      </div>
      <div class="head-controls">
        <div class="knob-unit">
          <div class="knob" id="rootknob" tabindex="0" role="slider"
               aria-label="Root note" aria-valuemin="0" aria-valuemax="11" aria-valuenow="0">
            <div class="knob-dial" id="rootdial"><span class="knob-ptr"></span></div>
          </div>
          <div class="unit-label">ROOT</div>
          <div class="led-readout" id="rootled">C</div>
        </div>
        <div class="filter-unit">
          <input id="filter" class="hw-input" type="search"
                 placeholder="name, Forte, flag&hellip;" aria-label="Filter recipes" />
          <div class="unit-label">FILTER</div>
        </div>
        <div class="power-led" title="ready" aria-hidden="true"></div>
      </div>
    </div>
  </header>

  <main class="wrap chd-main">
    <nav class="mod chd-index" aria-label="Chord recipes">
      <div class="mod-title">Recipes</div>
      <div class="idx-scroll" id="index"></div>
    </nav>
    <section class="mod chd-detail" aria-live="polite">
      <div class="mod-title">Voice</div>
      <div id="detail"></div>
    </section>
  </main>

  <section class="wrap manual">
    <div class="mod chd-refs">
      <div class="mod-title">Manual</div>
      <p class="manual-intro">{intro}</p>
      <h2>References</h2>
      {refs_html}
      <p class="chd-note">Prime forms and interval-class vectors are computed from
        first principles in <code>theory.py</code>; Forte numbers are drawn from the
        catalogue and pinned by tests. Set-class convention follows Rahn.{cite('rahn')}</p>
    </div>
  </section>

  <footer class="chd-foot"><div class="wrap">
    <span>Generated from the live catalogue &middot; <b>make chords</b> rebuilds it.</span>
    <span><a href="index.html">&larr; Music Generator</a></span>
  </div></footer>

<script id="chd-data" type="application/json">{data_json}</script>
<script>{_PAGE_JS}</script>
"""
    if not full_document:
        return f"<style>{_PAGE_CSS}</style>\n{body}"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Chord recipe reference — Music Generator</title>
  <meta name="description" content="Every chord recipe in the Music Generator, analysed: notes, audio, pitch-class set, prime form, Forte number, and interval-class vector, with cited sources." />
  <meta name="theme-color" content="#101215" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@500;600&display=swap" rel="stylesheet" />
  <style>{_PAGE_CSS}</style>
</head>
<body>
{body}
</body>
</html>
"""


def render_markdown(catalog: dict) -> str:
    recipes = catalog["recipes"]
    out = ["# Chord recipe reference",
           "",
           "*Reference &mdash; every named recipe usable in the `:recipe` slot of "
           "a colon chord token (e.g. `C::maj7`, `Bb:1:min9`). Generated by "
           "`chord_reference.py` (`make chords`) from `library/chord_recipes.py`, "
           "analysed by `theory.py`; do not hand-edit. See "
           "[token-grammar.md](token-grammar.md) for how recipes combine with "
           "roots, inversions, and slash bass, and "
           "[the interactive explorer](https://galenspikes.github.io/music-generator/chords.html).*",
           "",
           "Columns: **recipe**, semitone **offsets**, **notes** on C, **prime "
           "form**, **Forte** number[^forte], and **interval-class vector**[^forte]. "
           "Prime form follows Rahn.[^rahn]",
           ""]
    for cat in catalog["categories"]:
        out += [f"## {cat['title']}", "",
                "| recipe | offsets | notes on C | prime | Forte | ICV |",
                "|---|---|---|---|---|---|"]
        for name in cat["names"]:
            r = recipes[name]
            notes = " ".join(n["name"] for n in r["notes"])
            offs = " ".join(map(str, r["offsets"]))
            icv = "".join(map(str, r["icv"]))
            out.append(f"| `{name}` | {offs} | {notes} | "
                       f"{r['prime']} | {r['forte']} | {icv} |")
        out.append("")
    out += ["## References", ""]
    for key, text in REFERENCES:
        plain = re.sub(r"<[^>]+>", "", text)
        plain = (plain.replace("&ldquo;", "“").replace("&rdquo;", "”")
                 .replace("&amp;", "&").replace("&mdash;", "—"))
        out.append(f"[^{key}]: {plain}")
    out.append("")
    return "\n".join(out)


def main() -> int:
    import sys
    sys.path.insert(0, str(REPO / "library"))

    ap = argparse.ArgumentParser(description="Generate the chord-recipe reference.")
    ap.add_argument("--artifact", metavar="PATH",
                    help="also write a body-only build for the Artifact tool")
    args = ap.parse_args()

    catalog = build_catalog()
    n = len(catalog["recipes"])

    site = REPO / "site" / "chords.html"
    site.write_text(render_html(catalog, full_document=True), encoding="utf-8")
    print(f"wrote {site.relative_to(REPO)} ({n} recipes)")

    docs = REPO / "docs" / "reference" / "chord-recipes.md"
    docs.write_text(render_markdown(catalog), encoding="utf-8")
    print(f"wrote {docs.relative_to(REPO)}")

    if args.artifact:
        Path(args.artifact).write_text(
            render_html(catalog, full_document=False), encoding="utf-8")
        print(f"wrote {args.artifact} (Artifact body)")
    return 0


# CSS + JS are maintained as separate partials (site/_chords.*) and
# inlined at build time so the generated pages stay self-contained.
_ASSETS = REPO / "site"
_PAGE_CSS = (_ASSETS / "_chords.css").read_text(encoding="utf-8")
_PAGE_JS = (_ASSETS / "_chords.js").read_text(encoding="utf-8")

if __name__ == "__main__":
    raise SystemExit(main())
