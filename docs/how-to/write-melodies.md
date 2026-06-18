# How to write melodies

*Goal: add a monophonic line with `--melody`, written in scale degrees. See
[ADR-0005](../explanation/decisions/0005-scale-degree-melody.md) for why degrees.*

## A basic line

Degrees `1`–`7` relative to the key; duration prefixes as in percussion;
`|` barlines are ignored, `r` is a rest:

```bash
venv/bin/python music_generator.py --mode ostinato \
  --keys "C::maj7, G::7" --seconds 30 --out tune --no-play \
  --melody "q1 e2 e3 q5 | h2 q1 qr"
```

## Accidentals and octaves

```bash
# # / b before the degree; ' up an octave, , down
--melody "q1 e#4 q5 e3' | h b7 q1,"
```

## Key, mode, and anchoring

- The key/mode is **inferred from the chords**; override with `--melody-key` /
  `--melody-mode`.
- `--melody-relative key` resolves degrees against the section key;
  `--melody-relative chord` re-anchors to each chord's root (so one motif fits
  every chord).

```bash
--melody "q1 q3 q5 q3" --melody-relative chord --melody-key C --melody-mode major
```

## Transform the line

`--melody-transform {invert,retrograde,augment}` applies the fugal operations:

```bash
--melody "q1 e2 e3 q5" --melody-transform invert
```

## Tips
- Melodies are **space-separated** (because `,` is the octave-down mark), unlike the
  comma-separated chord/percussion tokens.
- `--melody-octave` shifts the whole line.

## See also
[ADR-0005 (scale degrees)](../explanation/decisions/0005-scale-degree-melody.md) ·
[token grammar §4](../reference/token-grammar.md)
