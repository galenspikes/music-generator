# Ecosystem & navigation plan

*Status: proposed. Captures two reported bugs and a plan to unify navigation
across the project's public surfaces so a visitor can move freely between the
showcase, the live instrument, the chord reference, and the docs.*

> **Update (resolved so far):**
> - **Bug B is fixed at the root** — the repo was made **public**, so every
>   `github.com/galenspikes/music-generator/…` link (grammar, CLI reference,
>   source, etc.) now resolves. Track 2 (publish styled docs) remains a nice-to-have,
>   not a fix.
> - **Bug A is fixed (interim)** — "Open the player" now points at the Hugging
>   Face Space, and its copy was trimmed to match what the Space actually offers.
>   When the React `webapp/` gets a public URL, repoint there and restore the
>   richer "per-voice / shareable settings" copy.
> - **The Space *is* now the React webapp (2026-07-04).** `space/app.py`'s
>   Gradio demo is retired; the Space builds and runs `webapp/` (FastAPI +
>   React) via the root `Dockerfile`, so "Open the player" already gets the
>   richer copy — no further repointing needed. `webapp/` is no longer
>   "local only" (see the table below).

---

## 1. The two reported bugs

### Bug A — "Open the player" button does nothing

- **Where:** `site/index.html:258`
- **What:** the button links to
  `https://claude.ai/code/artifact/4a87e4db-47a9-4b9f-a715-524c2729f740`.
- **Why it's broken:** that is a Claude Code *Artifact* URL — a private,
  session-scoped page, not a public destination. Every visitor who clicks it
  gets an auth wall / dead end. The surrounding copy promises a real
  interactive player ("swap the instrument on any voice, dial swing and stereo
  spread, then copy a link that reopens your exact settings").
- **Fix:** point it at a real public player. Today the only publicly hosted
  interactive instrument is the Hugging Face Space
  (`https://huggingface.co/spaces/gsp87/music-generator`) — the same target as
  the hero's "Try it live". Options: (a) repoint the button at the Space and
  dedupe the two CTAs, or (b) remove the button until the React web instrument
  (`webapp/`) is publicly deployed and can honor the "copy a link that reopens
  your settings" promise. **Decision needed** (see §4).

### Bug B — "Grammar link is broken"

- **Where:** `site/index.html:175` and `:525`, and `space/app.py:174`.
- **What:** all three link the grammar reference at
  `https://github.com/galenspikes/music-generator/blob/main/docs/reference/token-grammar.md`.
- **Why it's broken:** **the GitHub repo is private** (confirmed via the API:
  `"private": true`). A logged-out visitor — i.e. anyone on the public
  showcase or Space — gets GitHub's 404. The file exists; the link is
  unreachable *because of repo visibility*, not a bad path.
- **This is systemic, not a one-off.** Every `github.com/galenspikes/music-generator/...`
  link on a public surface is dead for the same reason. Current casualties:
  - `site/index.html`: grammar (×2), CLI reference (`:511`), "View on GitHub"
    (`:45`), footer GitHub link (`:521`).
  - `space/app.py`: grammar link (`:174`).
  - `webapp/frontend/src/App.jsx`: "source" (`:407`) and "docs" GitHub-tree
    link (`:408`).
  The grammar link is just the most-clicked symptom of "the public docs live
  behind a private repo."
- **Fix:** give the docs a real public home and link to *that* (see §3, Track 2),
  or make the repo public. Either unbreaks the grammar link at the root instead
  of patching one `href`.

---

## 2. The ecosystem today (why navigation is hard)

There are **four user-facing surfaces plus the docs tree, and they barely link
to each other** — several of the links that do exist are broken (§1).

| Surface | What it is | Where it lives | Nav out |
|---|---|---|---|
| **`site/`** | Static showcase: marketing homepage (`index.html`) + `chords.html` chord reference | GitHub Pages (`pages.yml`, on push to `main`) → `galenspikes.github.io/music-generator/` | anchors; → `chords.html`; → HF Space ("Try it live"); → GitHub (**broken, private**); → Claude artifact (**broken**) |
| **`webapp/`** | The React "web instrument": Listen / Library / Editor / **Docs** tabs. The Docs tab renders the *entire* `docs/` tree in-app (`/api/docs`) plus an interactive chord-recipe browser | Dev: local (FastAPI + Vite). **Prod: the actual public "try it live" instrument**, deployed as the Hugging Face Space via the root `Dockerfile`, auto-synced by `deploy-space.yml`. Footer expects the static site mounted at `/showcase/` | → GitHub source/docs (**broken, private**); → `/showcase/` (served in-container from `site/`) |
| **`space/`** | *(retired)* — used to be a separate Gradio demo (`space/app.py`); now just holds the Space's `README.md` (HF metadata). The Space itself now runs `webapp/`, see above. | — | — |
| **`docs/`** | The Diátaxis markdown tree — tutorials, how-to, reference (incl. the crown-jewel token grammar), explanation | **Not published anywhere public.** Only readable via the private repo or the webapp Docs tab (local) | in-tree relative links only |

### Structural problems

1. **The private repo is the root cause of the "broken links."** Every public
   link into GitHub 404s. The docs — including the grammar, described in
   `CLAUDE.md` as "the crown jewel" — have **no public URL at all**.
2. **`docs/` has no public home.** The webapp already has a lovely in-app
   renderer for the whole tree, but it only runs behind the local backend. On
   the open web there is nowhere to read the grammar.
3. **Surfaces don't cross-link coherently.** site → Space is one-way; the
   webapp expects the site at `/showcase/`; the Space links back to the site;
   nothing forms a consistent header. A visitor can't reliably hop
   showcase ↔ player ↔ chords ↔ docs.
4. **Two workflows fight over GitHub Pages.** `pages.yml` publishes `site/`;
   `deploy-web.yml` publishes a *different* artifact (a Pyodide PWA from `web/`
   on branch `claude/ios-app-feasibility-yozsr3`) to the **same** Pages site,
   sharing the `pages` concurrency group. Whichever ran last wins the root URL —
   so the webapp's `/showcase/` link and the Space's links into the site are
   only valid when `pages.yml` was the last to deploy. This is fragile and
   undocumented.
5. **Duplication with no "source of truth" marker.** The chord reference exists
   twice (static `chords.html` and the webapp recipe browser); the docs exist
   three ways (markdown, webapp render, broken blob links). Nothing says which
   is canonical.

---

## 3. The plan — a unified navigation model

Goal: one coherent "canopy" so any surface can reach any other in one click,
with no dead links. Ordered so the highest-leverage fixes come first.

### Track 0 — Stop the bleeding (quick, low-risk)

- **B-fix (player):** repoint `site/index.html:258` at the chosen public player
  (§4) — no more Claude-artifact link.
- **A-fix (grammar), interim:** until docs are published (Track 2), point the
  grammar/CLI links at a target that actually resolves for the public. If the
  repo will stay private short-term, either (a) inline a short grammar summary
  on the site, or (b) make the repo public now (unbreaks everything at once).

### Track 1 — Decide repo visibility (the unblocker)

Everything downstream depends on this. **Make the repo public**, or commit to
"no public link ever points at github.com/…". Public is by far the simplest —
it unbreaks the grammar link, the CLI reference, "View on GitHub", the webapp
"source"/"docs" links, and the Space grammar link *simultaneously*, and lets
Track 2 publish docs straight from the repo.

### Track 2 — Give `docs/` a public home ✅ done

- **Done:** added **MkDocs (Material)** — `mkdocs.yml` (Diátaxis-ordered nav
  over all 57 pages), `requirements-docs.txt` (`mkdocs-material`). The site
  builds locally with `mkdocs build` and is published to `/docs/` under the
  Pages root by the single `pages.yml` deploy (Track 3). Light/dark toggle,
  code-copy, section nav, and a footer link row back to showcase/instrument/repo.
- **Done:** every "Docs" link now points at the published site
  (`…github.io/music-generator/docs/`), and the homepage's grammar and CLI
  deep-links point at the styled pages
  (`…/docs/reference/token-grammar/`, `…/docs/reference/cli-reference/`).
- **Done (link cleanup):** the docs pages that linked repo *source files* with
  `../../voicing.py`-style paths (fine on GitHub, 404 on the MkDocs site) now use
  absolute GitHub URLs — 45 rewrites across the explanation and design-notes
  pages, plus the interactive chord page repointed at its live URL. Fixed the
  `decisions/` bare-directory links, a `song-studies/` link with no index page,
  and two stale heading anchors. The Pages build now runs **`mkdocs build
  --strict`**, so any future broken link fails CI instead of shipping.

### Track 3 — One Pages deployment, no collisions ✅ done

- **Done:** `deploy-web.yml` was retired. It was a manual workflow that built a
  Pyodide PWA from branch `claude/ios-app-feasibility-yozsr3` (no `web/` dir
  exists on `main`) and published it to the **Pages root**, clobbering the
  `site/` showcase whenever it ran. GitHub Pages serves one deploy, so the two
  workflows raced on the `pages` concurrency group — last writer won. The PWA
  work is preserved on its branch.
- **`pages.yml` is now the single authoritative Pages publisher** (`site/` at
  the root), and carries a header comment saying so.
- **To add another surface later** (docs from Track 2, or the PWA): assemble it
  into `pages.yml`'s artifact under a subpath rather than adding a second
  `deploy-pages` workflow. Proposed layout under the Pages root:
  - `/` → the `site/` showcase (homepage + `chords.html`)
  - `/docs/` → the MkDocs docs (Track 2)
  - `/app/` → the PWA / React instrument, *if/when* deployed (not the root)
- Follow-up: the webapp footer's `/showcase/` link (`App.jsx:409`) assumes the
  showcase is mounted at that path; point it at the showcase's real URL as part
  of Track 4 (shared nav).

### Track 4 — A shared navigation bar across every surface ✅ done

One canonical cross-surface set — **Home · Player · Chords · Docs · GitHub** —
now appears on every surface (each omits the link to itself), with identical
targets so "Docs" always means the same page:

- **Home** → `https://galenspikes.github.io/music-generator/`
- **Player** → the Hugging Face Space
- **Chords** → the showcase's `chords.html`
- **Docs** → `github.com/…/tree/main/docs` (public now; repoint to the MkDocs
  site once Track 2 ships)
- **GitHub** → the repo

Applied:
- `site/index.html`: added Docs + GitHub to the nav; CTA relabelled "Player →".
- `site/chords.html`: added a sticky top nav (previously only a footer
  back-link), styled to match the page's dark rack theme.
- `space/app.py`: link row realigned to Home · Chords · Docs · GitHub.
- `webapp` footer: realigned to home · chords · docs · github, and the broken
  relative `/showcase/` link now points at the showcase's real URL.

Also done: the webapp now carries the cross-surface nav in its **header** too
(Home · Chords · GitHub) — Player is the app itself and Docs is the in-app ❐ tab,
so both are omitted to avoid redundancy. The footer keeps the fuller set.

### Track 5 — De-duplicate, mark the source of truth ✅ done

- **Chord reference:** confirmed there's no data duplication — `library/chord_recipes.py`
  is the single source of truth (analysed by `theory.py`), and all three views
  derive from it: the generated `docs/reference/chord-recipes.md` table, the
  generated `site/chords.html` explorer (both from `chord_reference.py` /
  `make chords`), and the web instrument's in-app browser (live via
  `/api/recipes`). Documented this "one catalogue, three views" in
  `docs/reference/index.md`, and cross-linked the webapp's quick picker to the
  deep `chords.html` analyser.
- **Fixed a latent regression:** the Track 4 nav bar had been hand-added to the
  *generated* `site/chords.html`, so `make chords` would have wiped it. Moved
  the nav into the generator (`chord_reference.py` + the `site/_chords.css`
  partial) and repointed the generator's grammar/explorer links, so
  regeneration now emits the correct nav and links.
- **Docs:** MkDocs output (Track 2) is canonical for reading; the webapp Docs
  tab renders the same `docs/` tree in-app (`/api/docs`) and deliberately swaps
  the chord-recipes page for the interactive browser (`app.py` `_DOC_EXCLUDE`).

### Track 6 — Add the standalone Chord Recipes instrument to the shared nav ✅ done

A fifth surface joined the ecosystem: `webapp/chords-frontend/`, a standalone,
installable (PWA), tap-driven chord-progression builder + library, mounted at
`/chords` on the same backend as `webapp/`. Labeled **"ChordBuilder"** in the
shared nav (distinct from the existing **"Chords"** entry, which is the
read-only `chords.html` pitch-class analyser — "Chords" explains a recipe,
"ChordBuilder" composes a progression from them) and added, each surface
omitting itself:

- `site/index.html`: nav bar, a hero CTA ("Build a progression"), and the footer.
- `chord_reference.py` (the generator for `site/chords.html` — never hand-edit
  the generated file, see Track 5): nav bar.
- `webapp/frontend/src/App.jsx`: header nav and footer.
- `webapp/chords-frontend/src/App.jsx`: a new footer linking back to Home, the
  full instrument, the chord reference, and GitHub.

Deployment note: unlike "Player" (which links the `huggingface.co/spaces/…`
wrapper page), "ChordBuilder" links the Space's direct container URL
(`https://gsp87-music-generator.hf.space/chords/`) — the wrapper page embeds
the app in an iframe and doesn't forward arbitrary sub-paths, but the
Space's own `*.hf.space` subdomain serves the FastAPI app directly, so a
`/chords` sub-path resolves there. Confirmed reachable post-deploy.

---

## 4. Decisions needed before implementing

1. **Repo visibility** — make `galenspikes/music-generator` public, or keep it
   private and never link github.com from a public surface? (Gates Tracks 1–2
   and the real Bug B fix.)
2. **The "player"** — what should "Open the player" / "Try it live" point at:
   the HF Space (works today), or the React `webapp` once it's publicly deployed
   (matches the "reopen your exact settings" copy)? Should the two CTAs merge?
3. **Pages ownership** — confirm GitHub Pages serves the unified static hub
   (showcase + docs [+ app subpath]) and that `deploy-web.yml` moves off the
   root.

---

## 5. Appendix — exact link inventory to fix

| File:line | Current target | Problem | Action |
|---|---|---|---|
| `site/index.html:258` | `claude.ai/code/artifact/4a87e4db…` | Private artifact, dead | Repoint to public player |
| `site/index.html:175` | `…/blob/main/docs/reference/token-grammar.md` | Private repo → 404 | Point to published docs |
| `site/index.html:525` | same grammar blob URL | Private repo → 404 | Point to published docs |
| `site/index.html:511` | `…/blob/main/docs/reference/cli-reference.md` | Private repo → 404 | Point to published docs |
| `site/index.html:45,521` | repo homepage / GitHub | Private repo → 404 | Public repo, or drop |
| `space/app.py:174` | grammar blob URL | Private repo → 404 | Point to published docs |
| `webapp/frontend/src/App.jsx:407-408` | source + docs GitHub tree | Private repo → 404 | Public repo / published docs |
| `site/chords.html` | (no header nav) | Can't reach player/docs | Add shared nav bar |
