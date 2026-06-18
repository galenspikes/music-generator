# Architecture Decision Records (ADRs)

*One short, dated record per significant design decision. Format:
**Context → Decision → Rationale → Consequences → Status.** ADRs are immutable once
accepted — to change a decision, write a new ADR that supersedes the old one.*

Use **[0000-template.md](0000-template.md)** as the starting point.

## Index

| # | Decision | Status |
|---|---|---|
| [0000](0000-template.md) | *Template* | — |
| 0001 | Colon-delimited chord tokens (`root:inv:recipe/bass`) | *planned* |
| 0002 | Named chord recipes (vs. fixed quality families) | *planned* |
| 0003 | Probability inside the percussion token (`[prob]`) | *planned* |
| 0004 | One shared operator algebra (`*N`, `[...]*N`) across sub-languages | *planned* |
| 0005 | Scale degrees (not absolute pitches) for melody | *planned* |
| 0006 | Interrupters as probabilistic pattern substitution | *planned* |

*Rationale for 0001–0006 can draw on the documented design history; keep ADRs to
clean reasoning (context + why), not raw source material.*
