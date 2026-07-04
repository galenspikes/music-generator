# music-generator documentation

A token DSL for chords, percussion, and melody → harmony + voices + percussion →
MIDI, optionally rendered to audio. This is the documentation home.

The docs follow the **[Diátaxis](https://diataxis.fr/)** framework — four modes,
kept deliberately separate so each page does exactly one job:

| If you want to… | Go to | What it is |
|---|---|---|
| **Learn by doing**, start to finish | **[Tutorials](tutorials/)** | Guided lessons: from zero to a playing groove to a finished piece. |
| **Accomplish a specific task** | **[How-to guides](how-to/)** | Recipes: write a progression, build a beat, render audio. |
| **Look something up** | **[Reference](reference/)** | Dry, complete facts: the [token grammar](reference/token-grammar.md), every CLI flag, the chord-recipe catalog. |
| **Understand *why*** | **[Explanation](explanation/)** | The reasoning: [architecture](explanation/architecture.md), how harmony and percussion work, and the [design decisions](explanation/decisions/) behind the notation. |

## Two more sections

- **[Design notes](design-notes/)** — forward-looking *plans* (roadmap, arrangement,
  melody, lead-sheet import, refactor). These describe what is *intended*, not
  necessarily what exists today. Kept separate from the truth docs above on purpose.
- **[About](about/)** — provenance, contributing, and project history.

## Start here

- **Just want to hear it?** → run `make demo` (plays the flagship, *Kiss On My
  List*) or open the browser [demo gallery](https://galenspikes.github.io/music-generator/).
  The whole demo library — songs and capability presets — is
  `python cook_song.py list`.
- **New here?** → [Tutorial 1: Your first groove](tutorials/01-first-groove.md) *(planned)*
- **Want the big picture?** → [Architecture](explanation/architecture.md)
- **Writing tokens?** → [Token grammar reference](reference/token-grammar.md)
- **How the flagship is built** → [Kiss On My List study](explanation/song-studies/kiss-on-my-list.md)

---

*The crown jewel of this project is the token DSL. Never change a parser without
running the token tests; update [reference/token-grammar.md](reference/token-grammar.md)
if the grammar changes.*
