# Tutorial 1 — Your first groove

*A guided lesson: from a fresh clone to a looping groove you can hear, in a few
minutes. Follow every step in order; we favor a guaranteed result over options.*

## 1. Set up

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

For audio (optional but recommended), install the toolchain and have a SoundFont:

```bash
brew install fluidsynth ffmpeg     # macOS
```

`SoundFonts/` is gitignored — drop a `.sf2` file in there (any General MIDI
SoundFont works).

## 2. Generate your first piece (MIDI only)

```bash
venv/bin/python music_generator.py --mode ostinato \
  --keys "C::maj9, A::min11, F::maj7, G::7" \
  --perc-main "qb, eg, qc, eg, qb, eg, qc, eg" \
  --seconds 30 --out first_groove --no-play
```

You just made a 30-second looping groove: four lush chords over a kick/hat/snare
beat. The MIDI is under `output/midi/first_groove/`. Open it in any DAW or player.

## 3. Hear it (audio)

```bash
./play_music --save-wav --sf2 SoundFonts/your.sf2 \
  --mode ostinato \
  --keys "C::maj9, A::min11, F::maj7, G::7" \
  --perc-main "qb, eg, qc, eg, qb, eg, qc, eg" \
  --seconds 30 --out first_groove
```

A WAV lands under `output/audio/first_groove/` and plays.

## 4. Make it breathe

Add fills so the loop varies instead of repeating exactly. Append:

```bash
  --perc-interrupters "sc,sc,sd,sd,qc" "eb,eb,qi" \
  --perc-fill-rate 0.25
```

Now ~25% of cycles swap in a fill. Lower `--perc-fill-rate` to 0.05 for a hypnotic
lock; raise it to 0.4 for restlessness. That one knob is the heartbeat of the whole
project — see [how percussion works](../explanation/how-percussion-works.md).

## What you learned

- `--mode ostinato` + `--keys` = a looped progression in [colon tokens](../reference/token-grammar.md).
- `--perc-main` writes a beat; interrupters + `--perc-fill-rate` add variation.
- `--no-play` makes MIDI only; `./play_music --save-wav` renders audio.

**Next:** [Tutorial 2 — Your first song](02-your-first-song.md).
