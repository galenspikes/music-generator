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
    data_json = json.dumps(catalog, separators=(",", ":"))
    refs_html = render_references_html()
    intro = (
        "Every chord recipe in the generator, analysed. Pick one to see its "
        "notes on the keyboard, hear it, and read its pitch-class set "
        f"&mdash; normal and prime form{cite('rahn', 'straus')}, Forte "
        f"number{cite('forte')}, and interval-class vector{cite('forte')}.")
    body = f"""
  <header class="chd-hero">
    <div class="wrap">
      <p class="eyebrow">Reference &middot; pitch-class set analysis</p>
      <h1>Chord recipe reference</h1>
      <p class="lede">{intro}</p>
      <div class="chd-controls">
        <label class="ctl">Root
          <select id="root"></select>
        </label>
        <label class="ctl">Filter
          <input id="filter" type="search" placeholder="name, Forte, or flag&hellip;" />
        </label>
      </div>
    </div>
  </header>

  <main class="wrap chd-main">
    <nav class="chd-index" id="index" aria-label="Chord recipes"></nav>
    <section class="chd-detail" id="detail" aria-live="polite"></section>
  </main>

  <section class="wrap chd-refs">
    <h2>References</h2>
    {refs_html}
    <p class="chd-note">Prime forms and interval-class vectors are computed from
      first principles in <code>theory.py</code>; Forte numbers are drawn from the
      catalogue above and pinned by tests. Set-class convention follows Rahn.{cite('rahn')}</p>
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
  <meta name="theme-color" content="#f7f8fb" />
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
           "[/chords.html](../../site/chords.html) for the interactive explorer.*",
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


# --- inline CSS + JS (kept at the bottom so the logic above reads first) ------
_PAGE_CSS = """
:root{
  --paper:#f7f8fb; --surface:#fff; --surface-2:#eceff4; --ink:#14171d;
  --ink-2:#39414d; --muted:#646e7b; --line:#d7dce4; --line-2:#c2c9d3;
  --accent:#1b5aa0; --accent-deep:#143f72; --accent-wash:#e9f1fa;
  --serif:"IBM Plex Serif",Georgia,serif;
  --sans:"IBM Plex Sans",system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
}
*{box-sizing:border-box;}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
  font-size:17px;line-height:1.65;-webkit-font-smoothing:antialiased;}
.wrap{width:100%;max-width:1060px;margin:0 auto;padding:0 26px;}
a{color:var(--accent);text-decoration:none;}
a:hover{text-decoration:underline;text-underline-offset:2px;}
code{font-family:var(--mono);font-size:0.86em;background:var(--surface-2);
  border-radius:3px;padding:1px 5px;color:var(--accent-deep);}
sup.fn{font-size:0.62em;line-height:0;}
sup.fn a{color:var(--accent);padding:0 1px;font-family:var(--mono);}

.chd-hero{background:var(--surface);border-bottom:1px solid var(--line);
  padding:44px 0 30px;}
.eyebrow{font-family:var(--mono);font-size:0.68rem;font-weight:500;
  letter-spacing:0.18em;text-transform:uppercase;color:var(--accent);margin:0 0 14px;}
.chd-hero h1{font-family:var(--serif);font-size:clamp(2rem,4.5vw,2.7rem);
  font-weight:600;letter-spacing:-0.015em;margin:0 0 14px;}
.lede{font-size:1.05rem;color:var(--ink-2);max-width:66ch;margin:0 0 22px;}
.chd-controls{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-end;}
.ctl{display:flex;flex-direction:column;gap:5px;font-family:var(--mono);
  font-size:0.66rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;
  color:var(--muted);}
.ctl select,.ctl input{font-family:var(--mono);font-size:0.85rem;color:var(--ink);
  background:var(--surface);border:1px solid var(--line-2);border-radius:3px;
  padding:8px 10px;min-width:150px;}
.ctl select:focus-visible,.ctl input:focus-visible,.pbtn:focus-visible,
.idx-item:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}

.chd-main{display:grid;grid-template-columns:236px 1fr;gap:26px;
  align-items:start;padding-top:30px;padding-bottom:20px;}
.chd-index{position:sticky;top:14px;max-height:calc(100vh - 30px);overflow-y:auto;
  border:1px solid var(--line);border-radius:4px;background:var(--surface);
  padding:8px;}
.idx-cat{font-family:var(--mono);font-size:0.6rem;font-weight:600;
  letter-spacing:0.09em;text-transform:uppercase;color:var(--muted);
  padding:12px 8px 4px;}
.idx-item{display:block;width:100%;text-align:left;font-family:var(--mono);
  font-size:0.78rem;color:var(--ink-2);background:none;border:0;border-radius:3px;
  padding:5px 8px;cursor:pointer;}
.idx-item:hover{background:var(--surface-2);color:var(--ink);}
.idx-item.active{background:var(--accent-wash);color:var(--accent-deep);font-weight:600;}

.chd-detail{border:1px solid var(--line);border-radius:4px;background:var(--surface);
  padding:26px 28px;min-width:0;}
.d-head{display:flex;justify-content:space-between;gap:18px;align-items:baseline;
  flex-wrap:wrap;margin-bottom:18px;}
.d-name{font-family:var(--serif);font-size:1.7rem;font-weight:600;margin:0;}
.d-sub{font-family:var(--mono);font-size:0.66rem;letter-spacing:0.08em;
  text-transform:uppercase;color:var(--muted);margin-top:4px;}
.d-alias{font-size:0.82rem;color:var(--muted);margin-top:6px;}
.d-badges{display:flex;gap:8px;flex-wrap:wrap;}
.badge{font-family:var(--mono);font-size:0.72rem;color:var(--accent-deep);
  background:var(--accent-wash);border:1px solid #cadef1;border-radius:3px;
  padding:4px 9px;white-space:nowrap;}

.kbd{position:relative;height:132px;border:1px solid var(--line-2);
  border-radius:4px;background:#fff;overflow:hidden;margin:6px 0 16px;}
.kbd-white{position:absolute;top:0;bottom:0;background:#fff;
  border-right:1px solid var(--line);}
.kbd-white.on{background:var(--accent-wash);}
.kbd-black{position:absolute;top:0;height:62%;background:#2a2f38;border-radius:0 0 3px 3px;
  z-index:2;}
.kbd-black.on{background:var(--accent);}
.kbd-deg{position:absolute;left:0;right:0;bottom:6px;text-align:center;
  font-family:var(--mono);font-size:0.62rem;font-weight:600;color:var(--accent-deep);}
.kbd-deg-b{bottom:4px;color:#fff;}

.note-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;}
.note-chip{display:inline-flex;flex-direction:column;align-items:center;
  border:1px solid var(--line);border-radius:3px;padding:5px 11px;min-width:44px;
  background:var(--surface);}
.note-chip b{font-family:var(--serif);font-size:1.02rem;color:var(--ink);}
.note-chip i{font-family:var(--mono);font-size:0.64rem;font-style:normal;
  color:var(--muted);}

.transport{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:18px;
  padding-bottom:18px;border-bottom:1px solid var(--line);}
.pbtn{font-family:var(--mono);font-size:0.75rem;font-weight:500;color:var(--accent-deep);
  background:var(--surface);border:1px solid var(--line-2);border-radius:3px;
  padding:8px 13px;cursor:pointer;transition:background 0.1s ease;}
.pbtn:hover{background:var(--accent-wash);border-color:var(--accent);}
.pbtn.on{background:var(--accent);color:#fff;border-color:var(--accent);}
.pbtn.stop{color:var(--muted);}
.pbtn.stop:hover{color:#a53a24;border-color:#d8a99e;background:#fbeeea;}
.play-hint{font-family:var(--mono);font-size:0.66rem;color:var(--muted);
  text-transform:uppercase;letter-spacing:0.06em;margin-left:4px;}

.d-desc{font-size:0.98rem;color:var(--ink-2);margin:0 0 20px;max-width:66ch;}

.cons{margin:0 0 22px;max-width:520px;}
.cons-head{display:flex;justify-content:space-between;align-items:baseline;
  font-family:var(--mono);font-size:0.66rem;font-weight:600;letter-spacing:0.06em;
  text-transform:uppercase;color:var(--muted);margin-bottom:7px;}
.cons-band{color:var(--accent-deep);}
.cons-track{position:relative;height:10px;border-radius:5px;border:1px solid var(--line);
  background:linear-gradient(90deg,#2f8f6b 0%,#c9a13a 52%,#b4462f 100%);}
.cons-marker{position:absolute;top:-4px;width:3px;height:18px;border-radius:2px;
  background:var(--ink);box-shadow:0 0 0 2px rgba(255,255,255,0.85);transform:translateX(-1.5px);}
.cons-ends{display:flex;justify-content:space-between;font-family:var(--mono);
  font-size:0.6rem;color:var(--muted);margin-top:5px;text-transform:uppercase;
  letter-spacing:0.05em;}
.cons-read{font-family:var(--mono);font-size:0.68rem;color:var(--muted);margin-top:8px;}
.d-analysis{display:grid;grid-template-columns:auto 1fr;gap:9px 20px;margin:0;
  align-items:baseline;}
.d-analysis dt{font-family:var(--mono);font-size:0.66rem;font-weight:600;
  letter-spacing:0.06em;text-transform:uppercase;color:var(--muted);}
.d-analysis dd{margin:0;font-family:var(--mono);font-size:0.88rem;color:var(--ink);}
.icv-row{display:flex;gap:6px;flex-wrap:wrap;}
.icv-cell{display:inline-flex;flex-direction:column;align-items:center;
  border:1px solid var(--line);border-radius:3px;padding:2px 8px;min-width:30px;}
.icv-cell b{font-size:0.9rem;}
.icv-cell i{font-style:normal;font-size:0.58rem;color:var(--muted);}
.flag-row{display:flex;gap:6px;flex-wrap:wrap;}
.flag{font-family:var(--mono);font-size:0.66rem;color:var(--accent-deep);
  background:var(--accent-wash);border:1px solid #cadef1;border-radius:3px;
  padding:2px 8px;}

.chd-refs{padding:36px 0 10px;border-top:1px solid var(--line);}
.chd-refs h2{font-family:var(--serif);font-size:1.35rem;font-weight:600;margin:0 0 14px;}
.refs{margin:0;padding:0;list-style:none;counter-reset:none;}
.refs li{position:relative;font-size:0.9rem;color:var(--ink-2);margin:0 0 10px;
  padding-left:26px;max-width:78ch;}
.ref-n{position:absolute;left:0;font-family:var(--mono);font-size:0.78rem;
  color:var(--accent);font-weight:600;}
.ref-back{margin-left:6px;font-size:0.8rem;}
.chd-note{font-size:0.85rem;color:var(--muted);margin-top:16px;max-width:74ch;}

.chd-foot{border-top:1px solid var(--line);padding:26px 0;margin-top:20px;}
.chd-foot .wrap{display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;}
.chd-foot span{font-family:var(--mono);font-size:0.76rem;color:var(--muted);}

@media (max-width:760px){
  .chd-main{grid-template-columns:1fr;}
  .chd-index{position:static;max-height:none;
    display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:2px;}
  .idx-cat{grid-column:1/-1;}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important;}}
"""

_PAGE_JS = """
(function(){
  "use strict";
  var DATA=JSON.parse(document.getElementById("chd-data").textContent);
  var RECIPES=DATA.recipes, CATS=DATA.categories;
  var ROOTS=[{n:"C",pc:0,l:"C"},{n:"D\\u266d",pc:1,l:"D"},{n:"D",pc:2,l:"D"},
    {n:"E\\u266d",pc:3,l:"E"},{n:"E",pc:4,l:"E"},{n:"F",pc:5,l:"F"},
    {n:"F\\u266f",pc:6,l:"F"},{n:"G",pc:7,l:"G"},{n:"A\\u266d",pc:8,l:"A"},
    {n:"A",pc:9,l:"A"},{n:"B\\u266d",pc:10,l:"B"},{n:"B",pc:11,l:"B"}];
  var LETTERS=["C","D","E","F","G","A","B"], LPC={C:0,D:2,E:4,F:5,G:7,A:9,B:11};
  function spell(pc,step,rootPc,rootLetter){
    var letter=LETTERS[(LETTERS.indexOf(rootLetter)+step)%7];
    var acc=((pc-LPC[letter]+6)%12)-6; if(acc<=-3)acc+=12; if(acc>=3)acc-=12;
    var m=acc===-2?"\\ud834\\udd2b":acc===-1?"\\u266d":acc===1?"\\u266f":acc===2?"\\ud834\\udd2a":"";
    return letter+m;
  }
  var $=function(id){return document.getElementById(id);};
  function esc(s){return String(s).replace(/[&<>]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;"}[c];});}
  var state={name:null,root:0};

  var AC=null,master=null,active=[],loopTimer=null,mode=null;
  function ensureAudio(){
    if(!AC){ AC=new (window.AudioContext||window.webkitAudioContext)();
      master=AC.createGain(); master.gain.value=0.9; master.connect(AC.destination); }
    if(AC.state!=="running")AC.resume(); return AC;
  }
  function voice(midi,t0,sustain,dur,mul){
    var o=AC.createOscillator(); o.type="triangle";
    o.frequency.value=440*Math.pow(2,(midi-69)/12);
    var g=AC.createGain(), peak=0.13*(mul||1);
    g.gain.setValueAtTime(0.0001,t0);
    g.gain.exponentialRampToValueAtTime(peak,t0+0.014);
    o.connect(g); g.connect(master); o.start(t0);
    if(sustain){ g.gain.exponentialRampToValueAtTime(peak*0.72,t0+0.5); active.push({o:o,g:g}); }
    else { g.gain.exponentialRampToValueAtTime(0.0001,t0+dur); o.stop(t0+dur+0.06); }
  }
  function setMode(m){ mode=m;
    document.querySelectorAll(".pbtn[data-mode]").forEach(function(b){
      b.classList.toggle("on",b.dataset.mode===m); }); }
  function stopAll(){
    if(loopTimer){clearInterval(loopTimer);loopTimer=null;}
    if(AC){ var now=AC.currentTime;
      active.forEach(function(v){ try{ v.g.gain.cancelScheduledValues(now);
        v.g.gain.setValueAtTime(Math.max(0.0001,v.g.gain.value),now);
        v.g.gain.exponentialRampToValueAtTime(0.0001,now+0.2); v.o.stop(now+0.24);}catch(e){} }); }
    active=[]; setMode(null);
  }
  function voiced(){ var r=RECIPES[state.name], base=48+ROOTS[state.root].pc;
    return r.offsets.map(function(o){return base+o;}); }
  function doStrike(){ ensureAudio(); stopAll(); var t0=AC.currentTime+0.02;
    voiced().forEach(function(m){voice(m,t0,false,0.55,0.85);}); }
  function doSustain(){ ensureAudio(); stopAll(); var t0=AC.currentTime+0.02;
    voiced().forEach(function(m){voice(m,t0,true,0,0.68);}); setMode("sustain"); }
  function doArp(loop){ ensureAudio(); stopAll(); var ns=voiced(), i=0;
    function step(){ voice(ns[i%ns.length],AC.currentTime+0.01,false,0.42,0.95); i++;
      if(!loop && i>=ns.length && loopTimer){clearInterval(loopTimer);loopTimer=null;} }
    step(); loopTimer=setInterval(step,175); if(loop)setMode("loop"); }

  var LOW=48,HIGH=84,WHITE=[0,2,4,5,7,9,11];
  function drawKeyboard(container,voicedMidis,degByMidi){
    container.innerHTML="";
    var whites=[],blacks=[],wi=0;
    for(var m=LOW;m<=HIGH;m++){ var pc=m%12;
      if(WHITE.indexOf(pc)>=0){whites.push({m:m,i:wi});wi++;}
      else blacks.push({m:m,after:wi-1}); }
    var nW=wi;
    whites.forEach(function(k){
      var el=document.createElement("div"); el.className="kbd-white";
      el.style.left=(k.i/nW*100)+"%"; el.style.width=(100/nW)+"%";
      if(voicedMidis.indexOf(k.m)>=0){ el.className+=" on";
        var d=document.createElement("span"); d.className="kbd-deg";
        d.textContent=degByMidi[k.m]||""; el.appendChild(d); }
      container.appendChild(el);
    });
    blacks.forEach(function(k){
      var el=document.createElement("div"); el.className="kbd-black";
      var bw=100/nW*0.62;
      el.style.left=((k.after+1)/nW*100)+"%"; el.style.width=bw+"%";
      el.style.marginLeft=(-bw/2)+"%";
      if(voicedMidis.indexOf(k.m)>=0){ el.className+=" on";
        var d=document.createElement("span"); d.className="kbd-deg kbd-deg-b";
        d.textContent=degByMidi[k.m]||""; el.appendChild(d); }
      container.appendChild(el);
    });
  }

  var IC=["ic1 (m2/M7)","ic2 (M2/m7)","ic3 (m3/M6)","ic4 (M3/m6)","ic5 (P4/P5)","ic6 (tritone)"];
  function renderDetail(){
    var r=RECIPES[state.name]; if(!r)return;
    var root=ROOTS[state.root], base=48+root.pc;
    var vm=r.offsets.map(function(o){return base+o;});
    var degByMidi={}; r.notes.forEach(function(n){degByMidi[base+n.offset]=n.degree;});
    var chips=r.notes.map(function(n){
      var nm=spell(n.pc,n.step,root.pc,root.l);
      return '<span class="note-chip"><b>'+esc(nm)+'</b><i>'+esc(n.degree)+'</i></span>';
    }).join("");
    var icv=r.icv.map(function(v,i){return '<span class="icv-cell" title="'+IC[i]+'"><b>'+v+'</b><i>'+(i+1)+'</i></span>';}).join("");
    var flags=r.flags.map(function(f){return '<span class="flag">'+esc(f)+'</span>';}).join("");
    var aliases=r.aliases.length?'<div class="d-alias">identical set to '+r.aliases.map(function(a){return '<code>'+esc(a)+'</code>';}).join(", ")+'</div>':"";
    var pcs=r.notes.map(function(n){return n.pc;}).filter(function(v,i,a){return a.indexOf(v)===i;}).sort(function(x,y){return x-y;});
    var c=r.consonance, cp=Math.round(c.index*100);
    var hf='<sup class="fn"><a href="#ref-'+DATA.huron_ref+'">'+DATA.huron_ref+'</a></sup>';
    var meter='<div class="cons">'+
      '<div class="cons-head"><span>Consonance / dissonance'+hf+'</span>'+
        '<span class="cons-band">'+esc(c.band)+'</span></div>'+
      '<div class="cons-track"><div class="cons-marker" style="left:'+cp+'%"></div></div>'+
      '<div class="cons-ends"><span>consonant</span><span>dissonant</span></div>'+
      '<div class="cons-read">'+esc(c.reading)+' \\u00b7 Huron '+(c.score>=0?"+":"")+c.score.toFixed(2)+'/dyad</div>'+
      '</div>';
    $("detail").innerHTML=
      '<div class="d-head"><div><h2 class="d-name">'+esc(r.name)+'</h2>'+
        '<div class="d-sub">'+esc(r.category)+'</div>'+aliases+'</div>'+
        '<div class="d-badges"><span class="badge">prime '+esc(r.prime)+'</span>'+
        '<span class="badge">Forte '+esc(r.forte)+'</span></div></div>'+
      '<div class="kbd" id="kbd"></div>'+
      '<div class="note-row">'+chips+'</div>'+
      '<div class="transport">'+
        '<button class="pbtn" id="p-strike" title="One short chord">\\u25b7 Short</button>'+
        '<button class="pbtn" data-mode="sustain" id="p-sustain" title="Hold the chord">\\u25b7 Sustain</button>'+
        '<button class="pbtn" id="p-arp" title="Arpeggiate once">\\u25b7 Arpeggio</button>'+
        '<button class="pbtn" data-mode="loop" id="p-loop" title="Repeat the arpeggio">\\u21bb Loop</button>'+
        '<button class="pbtn stop" id="p-stop" title="Stop">\\u25a0</button>'+
        '<span class="play-hint">root '+esc(root.n)+'</span></div>'+
      (r.description?'<div class="d-desc">'+r.description+'</div>':"")+
      meter+
      '<dl class="d-analysis">'+
        '<dt>Pitch-class set</dt><dd>{'+pcs.join(", ")+'}</dd>'+
        '<dt>Prime form</dt><dd>'+esc(r.prime)+'</dd>'+
        '<dt>Forte number</dt><dd>'+esc(r.forte)+'</dd>'+
        '<dt>Interval-class vector</dt><dd class="icv-row">'+icv+'</dd>'+
        '<dt>Stacked intervals</dt><dd>'+esc(r.intervals.join(" \\u00b7 "))+'</dd>'+
        (flags?'<dt>Character</dt><dd class="flag-row">'+flags+'</dd>':"")+
      '</dl>';
    drawKeyboard($("kbd"),vm,degByMidi);
    $("p-strike").onclick=doStrike;
    $("p-sustain").onclick=doSustain;
    $("p-arp").onclick=function(){doArp(false);};
    $("p-loop").onclick=function(){ if(mode==="loop")stopAll(); else doArp(true); };
    $("p-stop").onclick=stopAll;
    var btns=document.querySelectorAll(".idx-item");
    for(var i=0;i<btns.length;i++)btns[i].classList.toggle("active",btns[i].dataset.name===state.name);
  }

  function buildIndex(){
    var idx=$("index");
    CATS.forEach(function(cat){
      var h=document.createElement("div"); h.className="idx-cat"; h.textContent=cat.title; idx.appendChild(h);
      cat.names.forEach(function(name){
        var b=document.createElement("button"); b.className="idx-item"; b.type="button";
        b.dataset.name=name; b.textContent=name;
        b.addEventListener("click",function(){select(name);});
        idx.appendChild(b);
      });
    });
  }
  function select(name){ if(!RECIPES[name])return; stopAll(); state.name=name; renderDetail();
    var el=document.querySelector('.idx-item[data-name="'+name+'"]');
    if(el&&el.scrollIntoView)el.scrollIntoView({block:"nearest"});
    if(history.replaceState)history.replaceState(null,"","#"+name);
  }
  function buildRoots(){
    var sel=$("root");
    ROOTS.forEach(function(r,i){var o=document.createElement("option");o.value=i;o.textContent=r.n;sel.appendChild(o);});
    sel.addEventListener("change",function(){state.root=+this.value;stopAll();renderDetail();});
  }
  function wireFilter(){
    $("filter").addEventListener("input",function(){
      var q=this.value.toLowerCase().trim();
      document.querySelectorAll(".idx-item").forEach(function(b){
        var r=RECIPES[b.dataset.name];
        var hay=(b.dataset.name+" "+r.forte+" "+r.prime+" "+r.flags.join(" ")+" "+r.category).toLowerCase();
        b.style.display=(!q||hay.indexOf(q)>=0)?"":"none";
      });
    });
  }
  function init(){
    buildRoots(); buildIndex(); wireFilter();
    var start=decodeURIComponent((location.hash||"").slice(1));
    if(!RECIPES[start])start=CATS[0].names[0];
    select(start);
    ["pointerdown","keydown"].forEach(function(ev){
      window.addEventListener(ev,function(){if(AC&&AC.state!=="running")AC.resume();},{passive:true});});
    window.__chords=function(){return {recipe:state.name,root:ROOTS[state.root].n,
      voiced:voiced(),audio:AC?AC.state:null,count:Object.keys(RECIPES).length};};
  }
  init();
})();
"""

if __name__ == "__main__":
    raise SystemExit(main())
