# Architecture Decision Records (ADRs)

*One short, dated record per significant design decision. Format:
**Context → Decision → Rationale → Consequences → Status.** ADRs are immutable once
accepted — to change a decision, write a new ADR that supersedes the old one.*

Use **[0000-template.md](0000-template.md)** as the starting point.

## Index

| # | Decision | Status |
|---|---|---|
| [0000](0000-template.md) | *Template* | — |
| [0001](0001-colon-chord-tokens.md) | Colon-delimited chord tokens (`root:inv:recipe/bass`) | Accepted |
| [0002](0002-named-chord-recipes.md) | Named chord recipes (vs. fixed quality families) | Accepted |
| [0003](0003-probability-in-the-token.md) | Probability inside the percussion token (`[prob]`) | Accepted |
| [0004](0004-shared-operator-algebra.md) | One shared operator algebra (`*N`, `[...]*N`) across sub-languages | Accepted |
| [0005](0005-scale-degree-melody.md) | Scale degrees (not absolute pitches) for melody | Accepted |
| [0006](0006-interrupters.md) | Interrupters as probabilistic pattern substitution | Accepted |

## A note on evidence

Each ADR separates **what the artifacts show** from **what is reconstructed**:

- **0001, 0002, 0006** draw on *dated, first-person* design reasoning (Sept 2025).
- **0005** has the project's *best-documented* rationale (a contemporaneous design
  memo weighing three options).
- **0003, 0004** have **no surviving design record** — the rationale is explicitly
  reconstructed from the design's structure, and each says so.

Every ADR also states the **prior art** honestly (Harte for 0001, the live-coding
lineage for 0003/0006, etc.). Do not cite an ADR's reconstructed rationale as if it
were primary evidence.
