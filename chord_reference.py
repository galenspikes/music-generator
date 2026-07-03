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
            "gloss": glosses.get(name, ""),
            "curated": CURATED.get(name, ""),
            "aliases": aliases,
        }
    order = [{"title": t, "names": ns} for t, ns in cats]
    return {"recipes": recipes, "categories": order}


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

.play-row{display:flex;align-items:center;gap:10px;margin-bottom:18px;
  padding-bottom:18px;border-bottom:1px solid var(--line);}
.pbtn{font-family:var(--mono);font-size:0.76rem;font-weight:500;color:#fff;
  background:var(--accent);border:1px solid var(--accent);border-radius:3px;
  padding:9px 16px;cursor:pointer;}
.pbtn:hover{background:var(--accent-deep);border-color:var(--accent-deep);}
.play-hint{font-family:var(--mono);font-size:0.68rem;color:var(--muted);
  text-transform:uppercase;letter-spacing:0.06em;}

.d-prose{font-size:0.98rem;color:var(--ink-2);margin:0 0 18px;max-width:64ch;}
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

  var AC=null;
  function ensureAudio(){ if(!AC){AC=new (window.AudioContext||window.webkitAudioContext)();}
    if(AC.state!=="running")AC.resume(); return AC; }
  function tone(midi,t0,dur,mul){
    var f=440*Math.pow(2,(midi-69)/12);
    var o=AC.createOscillator(); o.type="triangle"; o.frequency.value=f;
    var g=AC.createGain(); var peak=0.15*(mul||1);
    g.gain.setValueAtTime(0.0001,t0);
    g.gain.exponentialRampToValueAtTime(peak,t0+0.012);
    g.gain.exponentialRampToValueAtTime(0.0001,t0+dur);
    o.connect(g); g.connect(AC.destination); o.start(t0); o.stop(t0+dur+0.05);
  }
  function voiced(){ var r=RECIPES[state.name]; var base=48+ROOTS[state.root].pc;
    return r.offsets.map(function(o){return base+o;}); }
  function playBlock(){ ensureAudio(); var t0=AC.currentTime+0.03;
    voiced().forEach(function(m){tone(m,t0,1.5,0.85);}); }
  function playArp(){ ensureAudio(); var t0=AC.currentTime+0.03;
    voiced().forEach(function(m,i){tone(m,t0+i*0.16,1.1,1.0);}); }

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
    var prose=r.curated||(r.gloss?esc(r.gloss)+".":"");
    var pcs=r.notes.map(function(n){return n.pc;}).filter(function(v,i,a){return a.indexOf(v)===i;}).sort(function(x,y){return x-y;});
    $("detail").innerHTML=
      '<div class="d-head"><div><h2 class="d-name">'+esc(r.name)+'</h2>'+
        '<div class="d-sub">'+esc(r.category)+'</div>'+aliases+'</div>'+
        '<div class="d-badges"><span class="badge">prime '+esc(r.prime)+'</span>'+
        '<span class="badge">Forte '+esc(r.forte)+'</span></div></div>'+
      '<div class="kbd" id="kbd"></div>'+
      '<div class="note-row">'+chips+'</div>'+
      '<div class="play-row"><button class="pbtn" id="pblock">\\u25b6 Block</button>'+
        '<button class="pbtn" id="parp">\\u25b6 Arpeggio</button>'+
        '<span class="play-hint">root '+esc(root.n)+'</span></div>'+
      (prose?'<p class="d-prose">'+prose+'</p>':"")+
      '<dl class="d-analysis">'+
        '<dt>Pitch-class set</dt><dd>{'+pcs.join(", ")+'}</dd>'+
        '<dt>Prime form</dt><dd>'+esc(r.prime)+'</dd>'+
        '<dt>Forte number</dt><dd>'+esc(r.forte)+'</dd>'+
        '<dt>Interval-class vector</dt><dd class="icv-row">'+icv+'</dd>'+
        '<dt>Stacked intervals</dt><dd>'+esc(r.intervals.join(" \\u00b7 "))+'</dd>'+
        (flags?'<dt>Character</dt><dd class="flag-row">'+flags+'</dd>':"")+
      '</dl>';
    drawKeyboard($("kbd"),vm,degByMidi);
    $("pblock").addEventListener("click",playBlock);
    $("parp").addEventListener("click",playArp);
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
  function select(name){ if(!RECIPES[name])return; state.name=name; renderDetail();
    var el=document.querySelector('.idx-item[data-name="'+name+'"]');
    if(el&&el.scrollIntoView)el.scrollIntoView({block:"nearest"});
    if(history.replaceState)history.replaceState(null,"","#"+name);
  }
  function buildRoots(){
    var sel=$("root");
    ROOTS.forEach(function(r,i){var o=document.createElement("option");o.value=i;o.textContent=r.n;sel.appendChild(o);});
    sel.addEventListener("change",function(){state.root=+this.value;renderDetail();});
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
