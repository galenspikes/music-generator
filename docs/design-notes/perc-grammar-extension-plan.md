# Percussion grammar extensions — Euclidean rhythms & alternation

*Forward-looking. Proposes two additions to the percussion token language
(`--perc-main`, `--perc-interrupters`): a **Euclidean rhythm macro** `(K,N[,R])`
and a **cycle alternation construct** `<a|b|…>`. Both come from a review pass
(2026-07-08) comparing the DSL to its relatives — they are the two
TidalCycles mini-notation constructs with the highest power-per-character that
this grammar lacks, and both preserve the project's determinism/seed ethos.
Grammar changes are governed by the house rule: token tests
(`tests/test_tokens.py` / percussion tests) and
[token-grammar.md](../reference/token-grammar.md) update in the same commit as
any parser change.*

**Why these two.** The percussion language today has one variation mechanism:
interrupters, which are *stochastic* (fired by `fill_rate`). There is no
*deterministic* variation (play A this cycle, B the next) and no compact way to
write the asymmetric onset patterns that underpin most groove traditions.
Euclidean onsets cover the second (Toussaint, *"The Euclidean algorithm
generates traditional musical rhythms"*: E(3,8) = tresillo, E(5,8) = cinquillo,
rotations of E(5,16) = the son/bossa clave family — patterns the demo songs
currently hand-type). Alternation covers the first, as the deterministic
complement to interrupters.

The two constructs are **not equally shaped**, and the plan keeps them separate
because of it: the Euclid form is a pure expansion-time macro (like `*N`);
alternation must survive parsing and resolve per cycle at build time.

---

## 1. Euclidean rhythm macro — `TOKEN(K,N[,R])`

### Syntax & semantics

A parenthesized group after an otherwise-complete percussion token:

| Example | Expands to | Meaning |
|---|---|---|
| `sb(3,8)` | `sb, sr, sr, sb, sr, sr, sb, sr` | tresillo: 3 kick onsets over 8 sixteenth steps |
| `sbg(3,8)` | (as above, `bg` per onset) | kick+hat together on each onset |
| `sb[vel-15](3,8)` | onsets carry `[vel-15]` | modifiers apply to every onset |
| `sb(3,8,1)` | onset pattern rotated left 1 step | optional third arg = rotation (default 0) |
| `sb(3,8)*2` | the 8-token expansion, twice | `*N` repeats the expanded sequence |

- The token's **duration letter is the step size**; total length is always
  `N × dur` — predictable and grid-friendly.
- Non-onset steps become `<dur>r` rests.
- Onset placement is Bjorklund's algorithm (Toussaint's convention for
  rotation).
- `K = 0` → all rests; `K = N` → every step an onset; `K > N` or
  `N = 0` → parse error (loud, not clamped — consistent with the parser's
  existing error style).
- **Expansion order:** `(K,N,R)` expands first, then `*N` applies to the
  resulting sequence (equivalent to wrapping the expansion in `[…]*N`).

### Implementation

A **pre-parse string rewrite** in `percussion.py`, running alongside the
existing repetition expansion — the same macro layer as `*N` / `[…]*N`.
Downstream code (`parse_single_token`, grid quantisation, `PercStage` /
`PercPlan`, the webapp's `/api/parse-perc` chips and grid mode) sees only
ordinary tokens it already understands. The webapp chip strip will show the
*expanded* rhythm, which is a feature, not a leak: the user sees exactly what
E(3,8) means. Since expansions are uniform-duration, they also fit the step
grid cleanly.

**Scope:** percussion only in v1. A Euclid over melody degrees is imaginable
but unscoped; chord interrupters (`c`/`r`) get it for free since they share the
percussion parser.

---

## 2. Cycle alternation — `<a|b|…>`

### Syntax & semantics

A token position whose content depends on the cycle index:

```
qb, <qc|qi>, qb, qc      # snare on cycles 0,2,4…; open hat on 1,3,5…
```

- Branches separated by `|` (comma is the token separator; `|` is unused in
  the percussion language — it is only meaningful in melody, where it is an
  ignored barline).
- Resolves as `branches[cycle % len(branches)]` — **deterministic and
  seed-stable**, the indexed complement to `fill_rate`'s stochastic
  substitution.
- Each branch is a **single ordinary token** in v1 (modifiers allowed). Group
  branches (`<[qb,qc]|[qb,qi]>`) are deferred to a v2 — they multiply the
  parser and length-accounting surface and no current song needs them.
- **Interaction with interrupters:** alternation resolves *first* (it defines
  what this cycle's main pattern is); interrupter substitution may then still
  replace the whole cycle, exactly as today. One sentence in the grammar doc
  pins this order.
- A branch containing a Euclid group (`<sb(3,8)|sb(5,8)>`) is legal only if
  branch lengths match; otherwise a parse error. (Euclid expands first, so
  this falls out of length-checking, but the error message should say why.)

### Implementation

Unlike Euclid, this **cannot be macro-expanded away** — the cycle index does
not exist at parse time. The construct must survive into the parsed
representation and resolve in the cycle loop where the main pattern is laid
down each cycle (the same place `choose_perc_pattern` decides interrupter
substitution). Touches: the percussion parser, the pattern model, and the
timeline builder — so this lands under the integration smoke tests, after
Euclid.

**Webapp note:** the step grid cannot represent a pattern that differs per
cycle. Per the lossless-grid rule in
[webui-perc-editor-recommendations.md](webui-perc-editor-recommendations.md)
(edits must never silently drop data), a pattern containing `<…>` keeps the
field in code mode (grid disabled with a note) rather than showing branch 0
and destroying the others on the first toggle.

---

## Sequencing

1. **Euclid first.** Pre-parser rewrite, no model changes, pinned by token
   tests, one grammar-doc section. The lowest-risk grammar extension
   available, with immediate payoff in the song library (the clave/bossa
   family becomes one token).
2. **Alternation second.** Touches the pattern model and cycle loop; wants the
   smoke tests watching and the Euclid length-checking already in place.

Both commits follow the parser house rule: token tests + grammar-doc update
ride with the parser change, never separately.

## See also

[Token grammar](../reference/token-grammar.md) (the language being extended) ·
[How percussion works](../explanation/how-percussion-works.md) (cycle /
interrupter model) ·
[Web UI & percussion editor recommendations](webui-perc-editor-recommendations.md)
(the lossless-grid rule alternation must respect) ·
[Refactor plan](refactor-plan.md) (tests-as-safety-net discipline).
