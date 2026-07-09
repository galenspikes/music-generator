# Error codes

Every error the API surfaces carries a machine-readable classification:
an `error_type` (a coarse category the UI can switch on), a `code` (a
stable identifier for the exact failure family), and a human `suggestion`
with a concrete fix. The web API returns these in the error payload
(`GenerationError.as_dict()`); editors use them for inline feedback.

Classification is by exception type: parsers raise the typed exceptions in
`errors.py`, and `generator_api.classify_exception()` reads the class's
`error_type`/`code` and looks up the suggestion. Errors that arrive as bare
message strings (deep engine raises, `argparse` exits) fall back to
message-pattern matching in `generator_api.classify_error()`.

## Registry

| Code | error_type | Exception (`errors.py`) | Meaning | Suggested fix shown |
|---|---|---|---|---|
| `ERR_CHORD_001` | `invalid_chord` | `InvalidKeyError` | A chord root / key name isn't a note name (`Bad key 'ZZ'`). | Lists valid roots (C, Db, D, …) and the `C::maj7` form. |
| `ERR_CHORD_002` | `invalid_recipe` | `InvalidRecipeError` | Unknown chord recipe name, or a recipe with no tones. | Points at Docs → Chord Recipes for valid names. |
| `ERR_CHORD_003` | `invalid_chord` | `InvalidBassError` | Slash chord with a missing or unparseable bass note. | Shows the `C::maj7/G` form. |
| `ERR_PERC_001` | `invalid_drum` | `InvalidDrumLetterError` | A percussion letter not in the active drum map. | Lists the valid drum letters from the active map. |
| `ERR_DUR_001` | `invalid_duration` | `InvalidDurationError` | A rhythm token with a missing/unknown duration letter, or nothing after it. | Explains the `<duration><letters>` token shape. |
| `ERR_PRESET_001` | `invalid_preset` | `InvalidPresetError` | Unknown keys-preset name. | Check the spelling. |
| `ERR_SYNTAX_001` | `invalid_syntax` | `InvalidRepetitionError` | Malformed `*N` repetition or `[...]*N` chain. | Shows the `C*4` / `[C, G]*2` forms. |
| `ERR_SYNTAX_002` | `invalid_syntax` | `EmptyTokenError` | A token came out empty (stray comma, dangling `:`). | Look for the stray separator. |
| `ERR_SYNTAX_000` | `invalid_syntax` | `TokenSyntaxError` (base) | Any other DSL parse error (bad inversion, too many `:` sections, …). | Points at the token grammar doc. |
| `ERR_ARG_001` | `invalid_argument` | — (raised structured at the API boundary) | `seconds` out of the API's 0–600 range (non-positive or resource-abusive). | Pick a length from 1 to 600 seconds. |
| `ERR_ARG_002` | `invalid_argument` | — (raised structured at the API boundary) | `bpm` out of the API's 1–960 range. | Pick a tempo between 40 and 300 BPM. |
| `ERR_GEN_000` | `generation_error` | — (unclassified fallback) | Anything the registry doesn't recognise. | Points at the token grammar doc. |

## Conventions

- **Codes are stable**: a code never changes meaning; new failure families
  get new codes (`ERR_PERC_002`, …) rather than reusing old ones.
- **`error_type` is for UI routing** (which editor to highlight);
  **`code` is for programmatic handling and support** ("what exactly
  failed").
- **Adding a new error**: subclass `TokenSyntaxError` in `errors.py` with
  fresh `error_type`/`code`, add its suggestion to
  `generator_api._EXC_SUGGESTIONS`, document it here, and pin it in
  `tests/test_errors.py`.
