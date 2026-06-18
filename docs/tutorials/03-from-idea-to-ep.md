# Tutorial 3 — From idea to EP

*The real workflow: taking pieces from sketch to a finished, released set of
tracks. Less hand-holding than Tutorials 1–2 — this is how you actually work.*

This tutorial assumes you can already make a groove and a song. Here we focus on
the path from "I have ideas" to "I have an EP."

## 1. Sketch fast, in the instrument

Use the [web instrument](../how-to/use-the-web-instrument.md) (or the CLI) to
explore. Don't commit to anything — chase harmonic ideas, find a groove that feels
alive. Save the tokens of anything you like.

## 2. Promote a sketch to a song file

Move a promising idea into a `songs/*.yml` file (see
[Tutorial 2](02-your-first-song.md)). The YAML is your durable score — version it,
diff it, revise it. Give each track its own file.

## 3. Arrange for development

The hardest and most important step. A loop is not a track. For each piece, build
real sections and make them **go somewhere**:

- vary `instrument`, `satb`, `bass`, and especially `perc.fill_rate` across sections;
- add an intro that earns the first full statement, and an outro that resolves;
- be honest about the limit noted in
  [ADR-0006](../explanation/decisions/0006-interrupters.md): the engine gives you
  *non-repetition* for free, but *development* is your job, expressed through the
  arrangement.

## 4. Render and master

```bash
./play_music --save-wav --sf2 SoundFonts/your.sf2 \
  --song songs/track_01.yml --out track_01 --normalize
```

`--normalize` gives consistent loudness across tracks; add a small `--boost-db` if a
track sits quiet. Stems are split by default, so you can take the per-voice WAVs
into a DAW for real mixing if you want more than the built-in render.

## 5. Sequence the EP

Pick an order, check the tracks sit at consistent loudness, and release. The music
*is* the contribution — releasing it is how the work gets seen, and the only real
proof of what the instrument can do.

## Where to go deeper

- [How harmony works](../explanation/how-harmony-works.md) — shape the voicings.
- [Create an arrangement](../how-to/create-an-arrangement.md) — the YAML reference.
- The existing `songs/` files — worked templates across several styles.
