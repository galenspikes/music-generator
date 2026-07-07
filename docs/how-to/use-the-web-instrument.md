# How to use the web instrument

*Goal: make music in the browser — no install, no music theory required. Turn a
knob or edit a chord and it regenerates and plays instantly.*

Open the hosted instrument: **<https://gsp87-music-generator.hf.space/>**
(the landing page at <https://galenspikes.github.io/music-generator/> links to it too).
It loads with a demo already playing — press **▶** on the player and you're off.

## The four tabs

Across the top: **Listen · Library · Editor · Docs.**

- **Listen** — the player, a piano-roll of what's playing, and quick chord presets.
  This is where you *hear* the current patch.
- **Library** — pick a **demo song**, browse **your saved presets**, or **import a
  lead-sheet PDF**. Clicking any card loads it and jumps back to Listen.
- **Editor** — every control, grouped into modules (Harmony, Voicing, Bass,
  Percussion, …). This is where you *shape* the sound.
- **Docs** — this documentation, in-app.

## The transport (top bar)

- **BPM** — tempo. Drag right for faster.
- **Sound bank** — which set of instrument samples the browser plays through.
  *General MIDI* covers everything; *Salamander Piano* is piano-only (other
  instruments will sound wrong).
- **⚄ new take** — keeps all your settings but rerolls the random seed, so you get
  a fresh variation of the same idea. Great for "almost — give me another."
- The little lamp shows status: **generating** (with a live timer) → **ready**.

## What each knob does (and what to listen for)

You don't need to know them all. Every control has a **?** bubble — hover (or tap on
mobile) for a one-line explanation. The ones worth reaching for first:

- **Harmony › keys** — the chord progression itself, e.g.
  `C::maj7, A::min9, D::min7, G::13`. This is the heart of the piece. The chord
  presets on the Listen tab give you starting points; the
  [chord grammar](write-chord-progressions.md) explains the syntax.
- **Voicing › voicing** — *SATB* is clean four-part harmony; **switch to *dense*** and
  every chord tone sounds across the register — instantly lusher and more complex.
- **Voicing › satb-style** — *block* re-voices a fresh chord on every hit; **switch to
  *counterpoint*** and the voices break into flowing, independent lines.
- **Voicing › counterpoint-step** — with counterpoint on, **lower this** (e.g. 0.25)
  for faster, busier lines; raise it for calmer motion.
- **Percussion › perc fill rate** — **0 is a locked, repeating groove;** turn it up and
  the drums keep swapping in fills. At 1 they never sit still.
- **Bass › bass-style** — *follow* hugs the harmony; try *walking* for a jazz feel, or
  set it to *none* to hear the harmony bare.
- **Dynamics › swing** — nudge off 0 for a swung, human feel.

Change anything and it re-plays automatically — so the fastest way to learn a knob is
to move it and listen.

## Save and export your creation

- **Save** (top of the page) stores the current settings as a named **preset** — it
  shows up under *Library › My Presets*. Tick **"use as my home preset"** and the app
  will boot straight into it next time.
- **⤓ MIDI** (under the player on the Listen tab) downloads the current piece as a
  standard `.mid` file — drop it into any DAW (Logic, Ableton, GarageBand,
  MuseScore…) to keep composing with real instruments.
- Presets live in your browser session; MIDI is the portable, shareable artifact.

## What the demos showcase

Open **Library › Songs** and try a few — each highlights something different:

- A **jazz standard** (e.g. *Autumn Leaves*, *Kiss On My List*) — full arrangements
  with evolving percussion.
- A **dense / exotic-voicing** patch — hear what *voicing: dense* does to color.
- A **counterpoint** patch — baroque-style independent voices.
- A **percussion-forward** groove — where the drums, not the chords, drive it.

Loading a demo fills every control, so it doubles as a worked example: switch to the
**Editor** tab afterward to see *how* it was built, then start turning knobs.

## From exploring to composing

1. Load a demo close to the mood you want.
2. Change the **keys** to your own progression (or import a lead sheet).
3. Adjust **voicing**, **percussion**, and **tempo** to taste — use **⚄ new take**
   when you're close but not quite there.
4. **Save** it as a preset, and **⤓ MIDI** it out to finish in your DAW.

## Troubleshooting

- **It's silent.** Press **▶** on the player first (browsers block audio until you
  click). Then check: is **Percussion › perc-main** empty *and* the harmony muted?
  Is **bass-style** set to *none* with no other voice? Is the **Sound bank** set to
  *Salamander Piano* while you're using a non-piano instrument (that bank only has
  piano samples)?
- **A control did nothing.** Some only apply in context — e.g. *counterpoint-step*
  only matters when *satb-style* is *counterpoint*; *bass-step* is ignored when
  *bass-style* is *follow*. The **?** tooltip notes these.
- **An error popped up.** The toast tells you what's wrong (e.g. an unrecognized
  chord); click **Details** for the raw message. Fix the flagged field and it
  re-plays.
- **Song length looks off.** Songs use their own per-section lengths, so the
  *seconds* control is ignored while a song is loaded.

## Run it locally (developers)

The hosted Space runs this exact app; to run it yourself from a checkout, with the
project venv and Node installed:

```bash
# backend — FastAPI over generator_api.py (in-process generation)
PYTHONPATH=$PWD venv/bin/uvicorn app:app --app-dir webapp/backend --port 8753

# frontend — React + Vite
cd webapp/frontend && npm install && npm run dev
```

The Vite dev server proxies `/api` to the backend; open the printed localhost URL.

**How it's wired:** the backend is a thin FastAPI layer over `generator_api.py` (the
in-process seam — generation happens in memory and returns MIDI plus stem info); the
frontend's control surface is generated from the engine's own parameter schema, so it
always reflects the full feature set. The chord and percussion token editors write the
same tokens documented in the [token grammar](../reference/token-grammar.md).

## See also
[Write chord progressions](write-chord-progressions.md) ·
[Build percussion patterns](build-percussion-patterns.md) ·
[Import a lead sheet](import-a-lead-sheet.md) ·
[webapp/README.md](https://github.com/galenspikes/music-generator/blob/main/webapp/README.md) ·
[webapp UI design note](../design-notes/webapp-ui-design.md) ·
[architecture — web instrument](../explanation/architecture.md)
