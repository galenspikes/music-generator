# How to generate fugues and process music

*Goal: use the two special generator modes built on the melody primitive
(`melody.py`) — a fugal exposition and Reich/Glass-style minimalist process
pieces — instead of the chord/percussion engine.*

## Fugue (experimental)

Generate a fugal exposition from a melodic subject expressed in the
scale-degree [melody grammar](../reference/token-grammar.md). Voices enter
one at a time with the subject (tonic) and answer (dominant, the subject up
a fifth); the prior voice continues with the countersubject, and a cadence
closes the exposition.

```bash
venv/bin/python music_generator.py --fugue --instrument organ \
  --melody-key D --melody-mode minor --out fugue --no-play

./play_music --save-wav --no-play --fugue 'q1 q5 e4 e3 e2 e1 q7, q2 h1' \
  --instrument harpsi --melody-key C --melody-mode major \
  --sf2 SoundFonts/arachno.sf2 --fx lush --normalize --boost-normalize 2 --out fugue
```

Bare `--fugue` uses a built-in subject; pass one in scale-degree syntax to
use your own, and `--fugue-countersubject` to override the default
(`invert(subject)`). The answer is `transpose_diatonic(subject, 4)`.

This is an exposition only; episodes, middle entries in related keys, and
stretto and inversion devices are future work.

## Process music (experimental)

Minimalist process pieces from a single melodic cell (scale-degree
[grammar](../reference/token-grammar.md)), unfolding by rule:

- `phase` (Reich, *Piano Phase*): two voices loop the cell; the follower
  advances one note per stage, sweeping every alignment back to unison.
- `additive` (Glass): the cell grows a note at a time (1, 12, 123, ...) then
  contracts.
- `augment` (Reich, *Four Organs*): the cell's durations lengthen each stage.

```bash
./play_music --save-wav --no-play --process phase \
  --process-cell 's1 s2 s3 s5 s6 s5 s3 s2' --instrument 12 --bpm 160 \
  --melody-key E --melody-mode minor --sf2 SoundFonts/arachno.sf2 --out phase

venv/bin/python music_generator.py --process additive \
  --process-cell 'e1 e2 e3 e5 e7 e5 e3 e2' \
  --instrument organ --melody-key C --out additive --no-play
```

Tunables: `--process-cell`, `--process-reps` (stage length), and
`--process-stages` (for `augment`). Built on the melody primitive
(`process.py`).

## See also

- [Write melodies](write-melodies.md)
- [CLI reference](../reference/cli-reference.md)
