# Public API

What you can build against without it moving under you — and what is
internal plumbing that may change without notice. "Stable" here means: we
keep the signature and semantics working, and breaking changes get called
out loudly in the changelog/commit history. Anything not listed is internal.

Rule of thumb: **underscore-prefixed names are always internal**, in every
module, even when importable.

## The programmatic seam — `generator_api` (stable)

The contract the web UI (and any other embedder) builds on. In-memory: no
files under `output/` are touched.

| Name | Contract |
|---|---|
| `generate(spec) -> GenerationResult` | spec dict (CLI flag names as keys) → MIDI bytes + track info + warnings + envelope. Raises `GenerationError`. |
| `validate(spec) -> ValidationResult` | Can this spec generate? Failure message/suggestion, never raises. |
| `parameter_schema() -> list[dict]` | Every controllable flag, introspected from the CLI parser. |
| `parse_keys(keys, mode) -> dict` | Chord chart → structured chips/segments for editors. |
| `parse_perc(pattern, kind) -> dict` | Percussion / interrupter motif → per-token structured info. |
| `classify_exception(exc)` / `classify_error(msg)` | Error → `(error_type, suggestion, code)`. See [docs/reference/error-codes.md](docs/reference/error-codes.md). |
| `GenerationError` | Structured failure: `.error_type`, `.suggestion`, `.code`, `.as_dict()`. |
| `GenerationResult`, `ValidationResult`, `TrackInfo` | Result value objects (`.as_dict()` shapes are the web API's JSON). |
| `list_songs()` / `load_song(name)` | Song catalog (from `songs/*.yml`). |
| `list_presets()` / `load_preset()` / `save_preset()` / `delete_preset()` | User preset store. |
| `list_progressions()` / `load_progression()` / `save_progression()` / `delete_progression()` | Chord-progression store. |
| `slugify(name)` | Filesystem-safe identifier (the path-traversal guard). |
| `envelope_from_bytes(data, duration, buckets)` | MIDI bytes → note-density envelope for waveform visuals. |

## Typed errors — `errors` (stable)

The exception hierarchy parsers raise; all subclass `ValueError`.
`TokenSyntaxError` plus `InvalidKeyError`, `InvalidRecipeError`,
`InvalidBassError`, `InvalidDrumLetterError`, `InvalidDurationError`,
`InvalidPresetError`, `InvalidRepetitionError`, `EmptyTokenError` — each
carries a stable `error_type` and `code` class attribute.

## The DSL parsers (stable)

The token grammars are the project's core asset
([docs/reference/token-grammar.md](docs/reference/token-grammar.md)), and these are their reference
implementations:

- `tokens.key_roots(mode, keys_csv)`, `tokens.parse_colon_key_token(token)`,
  `tokens.parse_repetition_token(token)`, `tokens.parse_chain_repetition(token)`
- `percussion.parse_single_token(tok, drum_map=None)`,
  `percussion.parse_pattern(...)`, `percussion.parse_many_patterns(...)`
- `mtheory.parse_key_name(kname)`, `mtheory.resolve_instrument(arg)`

## Engine builders (stable-ish)

Useful for driving the engine directly (the CLI and `generator_api` share
them). Signatures are kept compatible, but they assume engine conventions
(beats, SATB tuples, the active drum map) that are still evolving toward
explicit context passing — expect keyword-only *additions*:

- `composition.build_progression`, `build_chord_timeline`,
  `build_dense_timeline`, `build_harmony_events`, `fill_chords_to_end`,
  `truncate_timeline_to`
- `voicing.realize_SATB`, `realize_dense`, `build_bass_line`,
  `build_arpeggio_events`, `build_counterpoint_lines`
- `midiout.MidiOut` (constructor + `chord_block`, `dense_block`,
  `drums_block`, `play_voice_note`, `save`, `write_stems`)
- `percussion.build_perc_from_args` and the `build_drum_timeline_*` family
- `music_generator.build_flat_midi(args)`, `build_parser()`,
  `apply_arg_normalization(args)`, `song_overrides_from_args(args, include)`
- `arrangement.load_spec(path, ...)`, `arrangement.render(spec, out)`
- `music_generator.SpecError`

## Re-exports through `music_generator`

`music_generator` star-re-exports every engine module's `__all__`, so
`mg.build_harmony_events`, `mg.parse_single_token`, `mg.MidiOut` etc. all
work. **Guaranteed**: every name listed above stays reachable both from its
home module and through `music_generator`. Anything else you find on `mg`
(logging setup, path constants, manifest helpers) is internal.

## Internal — do not build on

- Underscore-prefixed functions anywhere (`_describe_token`,
  `_counterpoint_sequence`, `_run`, …).
- `music_generator.main` / `_run` and the CLI output layout
  (`output/{midi,audio,metadata}/…`) — a rendering convention, not an API.
- `webapp/backend/app.py` HTTP routes — versioned by the frontend they
  serve, not by this contract (the JSON *shapes* come from the
  `generator_api` value objects above, which are stable).
- `render.py`, `render_gallery.py`, `chord_reference.py` internals — CLI
  tools; drive them via their command lines.
- Module-global state (`percussion._DRUM_MAP_CACHE`, the recipe cache):
  scheduled to become injected context (see
  `docs/design-notes/refactor-plan.md` Tier 5). Use `set_active_drum_map` /
  `get_drum_map` rather than the cache variables.
