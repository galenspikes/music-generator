# Trade-offs and alternatives — the large efforts (Phases 2–4)

*Forward-looking. Expands the three **large** phases of the
[gap analysis](gap-analysis.md) — tonal-distance (A4), transport (A2), and the UI
(A5) — into their design spaces: the real alternatives, what each costs, and a
recommendation. Recommendations are **proposals**, not decisions.*

---

## Current reality that constrains the space

Four facts about today's system bound every choice below:

1. **Synthesis is already client-side.** The backend returns **MIDI bytes**, not
   audio ([webapp/backend/app.py:13](https://github.com/galenspikes/music-generator/blob/main/webapp/backend/app.py)); the browser plays
   them with `html-midi-player` + Tone.js + `@magenta/music` and a hosted soundfont
   ([webapp/frontend/src/App.jsx:283](https://github.com/galenspikes/music-generator/blob/main/webapp/frontend/src/App.jsx)).
2. **The current loop is already "fast re-render."** Tweak a param → `POST
   /api/generate` → sub-second in-process render → reload the player. Changes land on
   the *next* load, not live.
3. **The engine is deterministic / seedable.** `build_flat_midi` guarantees identical
   output for a given seed. The project's ethos is hand-authored and reproducible.
4. **Two synthesis paths already exist, and stay unmerged — decided.** Browser
   preview uses a soundfont hosted in the specific pre-converted directory format
   `html-midi-player`/Magenta.js requires (per-note sample files + a JSON
   manifest) — only two such directories are publicly known to exist:
   `sgm_plus` (full General MIDI, the default) and `salamander` (a high-quality
   *piano-only* bank, program 0 only). Master render uses FluidSynth + any local
   `.sf2` file (`render.py --sf2`, now with `--list-soundfonts` / bare-name
   resolution against `SoundFonts/`, see
   [ui-ux-roadmap.md](ui-ux-roadmap.md) Thread D). **Unifying them would mean
   converting arbitrary `.sf2` files into the browser's directory format** — a
   real audio-processing subsystem (re-sampling every instrument's velocity
   layers into individual encoded audio files plus a manifest), not a config
   change. That's out of scope, so the split is permanent by choice, not by
   neglect: preview picks from the 2 known browser-compatible banks (plus a
   custom-URL escape hatch for anyone hosting their own in that format); master
   picks from any local `.sf2`. Preview ≠ final was always going to be true here.

---

## Cross-cutting trade-offs (these recur in every phase)

- **Reuse the Python engine vs. port to JS/WASM.** The token DSL is central to the
  project; a JS reimplementation risks divergence and double-maintenance. **Principle:**
  keep the engine authoritative in Python and have it emit *events*; let the browser
  *schedule and synthesize*. This thread runs through Phases 3 and 4.
- **Determinism vs. learned/stochastic behavior.** Anything trained or heavily random
  fights fact #3 (reproducibility, seedable renders) and the hand-authored ethos.
- **Preview vs. master fidelity** (fact #4) — **decided: deliberate split**, not
  unified. See fact #4 above for why unifying isn't a small change.
- **Hosting cost / the public path.** The going-public + HF-Space direction favors
  *client-side* work (cheap, stateless) over *stateful per-connection servers*.

---

## Phase 2 — Tonal-distance / shaped deviation (A4)

**Goal:** a computed "distance from home" that rises with departure and biases toward
resolution, so deviation becomes a *shaped arc* rather than a flat probability.

| Approach | Pros | Cons |
|---|---|---|
| **A. Rule-based heuristic** — tension = weighted sum of fifths-distance, non-diatonic tones, register spread, density | interpretable, deterministic, cheap, fits the functional-harmony framing | taste-laden weights; collapsing tension to one number loses nuance; tuning is fiddly |
| **B. Formal model — Lerdahl *Tonal Pitch Space*** | principled, published, listener-validated; a real distance metric | substantial to implement; tuned for common-practice harmony — fights the project's chromatic-mediant/quartal taste |
| **C. Data-driven (Markov / learned expectation, à la Huron)** | captures real stylistic surprise; theoretically elegant ("deviation = surprisal") | needs a corpus + training; opaque, non-deterministic — **against fact #3**; heavy deps |
| **D. Single "intensity" macro knob** — one slider drives existing params (`fill_rate`, extension richness, register, activity) along a hand-tuned curve | tiny effort; immediate "arc" UX; reversible | not a real tension *model*; no harmonic awareness; won't *resolve* intelligently |

**Trade-off axis:** principled-but-expensive (B, C) vs. pragmatic-but-shallow (A, D);
and interpretable+deterministic (A, B, D) vs. data-driven (C).

**Recommendation:** **D now, A next.** Ship the macro knob to get the shaped-arc feel
cheaply, then grow it into the heuristic model (A) — which is where the
functional-harmony idea actually lives in code. Borrow TPS's *distances* (B) as the
metric inside A where they help. Treat C as off-ethos for this project.

---

## Phase 3 — The transport (the instrument) (A2)

**Goal:** a running clock that idles on the home and accepts **live** modulation —
press play, bend a knob, hear it — instead of re-compiling a finished file.

Note: option C below is essentially **today's behavior**, so the real decision is
whether to move *past* re-render-and-reload toward live scheduling.

| Approach | Pros | Cons |
|---|---|---|
| **A. Client-side live transport** — engine emits *events*; browser schedules them on Tone.Transport with lookahead and applies live param changes | true live feel; builds on the existing Tone.js + soundfont stack; Python stays authoritative for *logic*; cheap hosting | needs an events API (not baked MIDI); live edits need the engine's deviation logic queryable incrementally (or partly in JS); "idle forever" means an *infinite* event stream vs today's finite render; seed handling across edits |
| **B. Server-side transport, events over WebSocket** — Python runs the clock, streams events; browser synthesizes | Python fully authoritative; reuse all deviation logic live | stateful per-connection server (**against cost/public path**); event-latency on every gesture; more infra |
| **C. Polished "fast re-render + reload" (status quo+)** — keep re-rendering whole MIDI, swap seamlessly at loop boundaries | ~zero architecture change; already works; deterministic; cheap | not real-time (changes land next loop); re-render cost grows with length; reload breaks continuity — the theremin "now" is impossible |
| **D. Server audio streaming (FluidSynth real-time over WebRTC/WS)** | master-grade audio, live; consistent with the final render | heaviest infra; audio-stream latency; stateful server; **discards the working client-side player** |

**Trade-off axis:** where the clock lives (client / server / —) × true-live vs.
loop-quantized × reuse-engine vs. port-logic.

**Recommendation:** **A**, with **C** as the interim that already ships. A is the only
option that delivers M4 (live bend) while honoring "reuse the Python engine" and the
cheap-hosting path — its real cost is turning the engine into an *event source* that
can extend an infinite, seed-stable stream. **Reject D** (it throws away the existing
client-side synthesis for the heaviest infra) and treat **B** as a fallback only if
live-querying the deviation logic in JS proves intractable.

---

## Phase 4 — Present it: the UI (A5)

**Goal:** present the home already running and expose deviations as visible, gestural
controls. Today's frontend is already a structured React editor
([controls.jsx](https://github.com/galenspikes/music-generator/blob/main/webapp/frontend/src/controls.jsx), `HarmonyEditor`,
`PercEditor`) + a client MIDI player — i.e. a polished version of option B below.

**Hard dependency:** the gestural controls only *feel* live if **Phase 3A** exists.
Without it, every knob triggers a re-render (option C), and the UI is a fast settings
panel, not an instrument.

| Approach | Pros | Cons |
|---|---|---|
| **A. Skeuomorphic instrument surface** (the Bazille / DM-1 direction) | matches the product vision; emotionally "an instrument"; home-always-running is natural | high design + frontend cost; bespoke knob/drag components; touch/accessibility risk; hollow without Phase 3A |
| **B. Evolve the existing structured editor** — group "Home" vs "Deviations", live preview | cheap, accessible, maps to the existing spec/API; ships fast; partly built | feels like a settings page; only partially meets M5 ("intuitive, shown what to do") |
| **C. Timeline / arrangement editor** | powerful; supports the shaped arc; familiar to musicians | complex; reintroduces the *composer* paradigm the project is moving away from |
| **D. Hybrid — a "performance" surface over an "edit" drawer** | serves instrument-feel *and* depth; progressive disclosure; directly expresses "home + antennae" | two UIs to design/maintain; performance layer still needs Phase 3A to be real |

**Trade-off axis:** instrument-feel vs. build-cost vs. power/depth — gated by whether
Phase 3 has made anything live to expose.

**Recommendation:** **D, grown out of B.** Keep evolving the working editor (B) for
depth, and add a small **performance surface** (a few big always-on gestural controls)
as the front door — but only invest in the skeuomorphic polish (A) *after* Phase 3A
makes the controls respond live. Until then, B with grouped Home/Deviation sections is
the honest most-value-per-effort step. The preview-vs-master soundfont question
(fact #4) is now decided (deliberate split) — see fact #4 above.

---

## See also

[Gap analysis](gap-analysis.md) · [Stasis and function](../explanation/stasis-and-function.md) ·
[Webapp UI design](webapp-ui-design.md) · [Roadmap phase 2](roadmap-phase2.md)
