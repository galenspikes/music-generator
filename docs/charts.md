# Saved charts & recipes

Curated from old scratch files (`misc/scratch`, `misc/scratch2`, `misc/scratch.sh`)
before they were removed. These are the **named / annotated keepers** — the ones
worth turning into real `song_cookbook.py` entries. The full unedited scratch
files remain recoverable from git history.

> **Goal note (from scratch2):** "generative music… I would like to release some
> of these in an album or EP. Want: billie jean, mathrock_blues_A (name tbd),
> superstition."

> **Note:** These commands predate the repo move. Before running, fix:
> - SoundFont path: scratch uses `~/SoundFonts/Arachno.sf2` / `$HOME/SoundFonts/arachno.sf2`;
>   the file now lives at `SoundFonts/arachno.sf2` (lowercase) inside the repo.
> - Some use `--chord-len` (short form). Confirm the live flag name in the engine.

---

## mathrock_blues_A — "THIS WAS GREAT" (20-min version)

> Comment in original: *"THIS WAS GREAT / MAKE A SHORTER VERSION AND WE ARE GOOD."*
> A 300s (5-min) variant existed with the same chart.

```bash
./play_music \
  --seconds 1200 \
  --bpm 176 \
  --instrument saw \
  --mode ostinato \
  --keys 'A,A,A,A,D,D,A,A,E,D,A,E' \
  --chords triads sevenths ninths quartal sus add6 \
  --chords-order roundrobin \
  --chord-len e \
  --perc-main 'sbg,sr,sg,sb,scg,sr,sg,sb,sg,sr,sbg,sr,scg,sr,sg,sb' \
  --perc-interrupters 'sq,ss,st,su,sv,sv,su,st,ss,sq,scg,sg,sg,sj,sg,sg' \
  --perc-fill-rate 0.28 \
  --sf2 ~/SoundFonts/arachno.sf2 \
  --gain 0.7 --reverb 1 --chorus 1 --poly 768 \
  --chorus-super \
  --normalize --boost-normalize 2 \
  --out mathrock_blues_A
```

---

## billie jean — "this is the one"

```bash
./play_music \
  --seconds 300 \
  --bpm 117 \
  --instrument saw \
  --mode ostinato \
  --keys 'F#m,F#m,F#m,G#m,G#m,G#m,G#m,G#m, A,A,A,G#m,G#m,G#m,G#m,G#m' \
  --chords sevenths sevenths sevenths ninths sus add6 \
  --chords-order random \
  --chord-len e \
  --chord-fill-rate 0.06 \
  --perc-main 'ebg,eg,ecg,ebg,eg,eg,ecg,eg, ebg,eg,ecg,ebg,eg,ei,ecg,eg' \
  --perc-interrupters \
    'eg,eg,ecg,eg,eg,eg,ecg,eg' \
    'eg,ec,ecg,eg,ec,eg,ecg,eg' \
    'es,eg,et,ecg,eu,eg,ev,ecg' \
  --perc-fill-rate 0.1 \
  --sf2 ~/SoundFonts/arachno.sf2 \
  --gain 0.45 --reverb 0 --chorus 0 --poly 512 \
  --out billiejean_vamp_dry
```

---

## superstition (full-form, dry)

```bash
./play_music \
  --seconds 60 \
  --bpm 104 \
  --instrument saw \
  --mode ostinato \
  --keys 'Eb,Eb,Eb,Eb,Eb,Eb,Eb,Eb,Eb,Eb,Eb,Eb,Eb,Eb,Eb,Eb,B,B,C,C,B,B,Bb,Bb,A,A,A,A,B,B,B,B' \
  --chords sevenths ninths extended-chords lyd-dom sus \
  --chords-order roundrobin \
  --chord-len q \
  --chord-fill-rate 0.18 \
  --perc-main 'qb,qg,qc,qg' \
  --perc-interrupters 'sb,sg,scg,sg' \
  --perc-fill-rate 0.16 \
  --sf2 ~/SoundFonts/arachno.sf2 \
  --gain 0.50 --reverb 0 --chorus 0 --poly 512 \
  --out superstition_fullform_dry
```

A longer hybrid-drive variant (`superstition_hybrid_drive_dry`, 120s @ 116 bpm,
expanded chart + 16th perc-main) is in git history.

---

## I GOT RHYTHM / rhythm changes (Cherokee, dry)

```bash
./play_music \
  --seconds 200 \
  --bpm 200 \
  --instrument saw \
  --mode ostinato \
  --keys 'Bb,Bb,Gm,Gm,Cm,Cm,F,F, Dm,Dm,Gm,Gm,Cm,Cm,F,F, Bb,Bb,Bb,Bb,Eb,Eb,Em,Em, Bb,Bb,F,F,Bb,Bb,F,F,  Bb,Bb,Gm,Gm,Cm,Cm,F,F, Dm,Dm,Gm,Gm,Cm,Cm,F,F, Bb,Bb,Bb,Bb,Eb,Eb,Em,Em, Bb,Bb,F,F,Bb,Bb,F,F,  D,D,D,D,D,D,D,D, G,G,G,G,G,G,G,G, C,C,C,C,C,C,C,C, F,F,F,F,F,F,F,F,  D,D,D,D,D,D,D,D, G,G,G,G,G,G,G,G, C,C,C,C,C,C,C,C, F,F,F,F,F,F,F,F,  Bb,Bb,Gm,Gm,Cm,Cm,F,F, Dm,Dm,Gm,Gm,Cm,Cm,F,F, Bb,Bb,Bb,Bb,Eb,Eb,Em,Em, Bb,Bb,F,F,Bb,Bb,F,F' \
  --chords sevenths sevenths sevenths sevenths triads ninths add6 \
  --chords-order roundrobin \
  --chord-len q \
  --chord-fill-rate 0.30 \
  --chord-interrupters \
    'er,ec,er,ec, ec,er,ec,er' 'ec,er,ec,er, er,ec,er,ec' 'er,er,ec,er, ec,er,er,ec' \
    'ec,er,er,ec, er,ec,er,er' 'er,ec,er,er, ec,ec,er,ec' 'ec,er,ec,er, ec,er,er,er' \
    'er,ec,er,ec, ec,er,er,ec' 'ec,er,er,er, ec,er,ec,ec' \
  --perc-main 'ek,eg,ekh,ec, ek,eg,ekh,eg' \
  --perc-interrupters \
    'eg,eg,ecg,eg,eg,eg,ecg,eg' 'eg,ec,eg,ec,eg,ec,ecg,eg' 'eb,eg,ecg,eg,eb,eg,ecg,eg' \
    'es,et,eu,ev,es,et,eu,ev' 'ecg,es,ecg,et,ecg,eu,ecg,ev' 'eg,eg,ecg,eg,eg,eg,ecg,eh' \
    'eb,ecg,eg,eb,eg,ecg,eg,eg' 'eg,ecl,eg,ecg,eg,eg,ecg,eg' \
  --perc-fill-rate 0.09 \
  --sf2 ~/SoundFonts/arachno.sf2 \
  --gain 0.40 --reverb 0 --chorus 0 --poly 768 \
  --out rhythm_changes_bb_cherokee_dry
```

A fast (320 bpm) `rhythm_changes_bb_fast` variant on a Bb/G/C/F vamp is in git history.

---

## ALL THE THINGS YOU ARE (dry)

```bash
./play_music \
  --seconds 120 \
  --bpm 160 \
  --instrument saw \
  --mode ostinato \
  --keys 'F,F,F,F, Bb,Bb,Bb,Bb, Eb,Eb,Eb,Eb, Ab,Ab,Ab,Ab, Db,Db,Db,Db, G,G,G,G, C,C,C,C, C,C,C,C,  F,F,F,F, Bb,Bb,Bb,Bb, Eb,Eb,Eb,Eb, Ab,Ab,Ab,Ab, Db,Db,Db,Db, G,G,G,G, C,C,C,C, C,C,C,C,  E,E,E,E, A,A,A,A, D,D,D,D, G,G,G,G, C,C,C,C, F#,F#,F#,F#, B,B,B,B, B,B,B,B,  F,F,F,F, Bb,Bb,Bb,Bb, Eb,Eb,Eb,Eb, Ab,Ab,Ab,Ab, Db,Db,Db,Db, G,G,G,G, C,C,C,C, C,C,C,C,  F,F,F,F, Bb,Bb,Bb,Bb, Eb,Eb,Eb,Eb, Ab,Ab,Ab,Ab' \
  --chords sevenths ninths \
  --chords-order roundrobin \
  --chord-len q \
  --chord-fill-rate 0.25 \
  --chord-interrupters \
    'er,ec,er,ec, ec,er,ec,er' 'ec,er,ec,er, er,ec,er,ec' 'er,er,ec,er, ec,er,er,ec' \
    'ec,er,er,ec, er,ec,er,er' 'er,ec,er,er, ec,ec,er,ec' \
  --perc-main 'ek,eg,ekh,ec, ek,eg,ekh,eg' \
  --perc-interrupters \
    'eg,eg,ecg,eg,eg,eg,ecg,eg' 'eg,ec,eg,ec,eg,ec,ecg,eg' 'eb,eg,ecg,eg,eb,eg,ecg,eg' \
    'es,et,eu,ev,es,et,eu,ev' 'ecg,es,ecg,et,ecg,eu,ecg,ev' \
  --perc-fill-rate 0.12 \
  --sf2 ~/SoundFonts/arachno.sf2 \
  --gain 0.40 --reverb 0 --chorus 0 --poly 768 \
  --out allthethings_ab_dry
```

A `..._plus` variant with 24 chord-interrupter patterns and a broader chord
palette is in git history.

---

## rite of spring / "Augurs" ostinato

> Comment in original: *"rite of spring / doesnt work this sucks"* — kept for
> reference; the chromatic E/Eb ostinato idea may be worth revisiting.

```bash
./play_music \
  --seconds 300 --bpm 150 --instrument saw --mode ostinato \
  --keys 'E,Eb,E,Eb,E,Eb,E,Eb, E,Eb,E,Eb,E,Eb,E,Eb, E,Eb,E,Eb,E,Eb,E,Eb' \
  --chords triads sevenths --chords-order roundrobin --chord-len e --chord-fill-rate 0.22 \
  --chord-interrupters 'er,ec,er,ec,sc' 'er,ec,ec,ec,sc' 'ec,er,ec,ec,sc' \
  --perc-main 'ebg,eg,eg,eg,eg,ebg,ebg,ecg' --perc-fill-rate 0.00 \
  --sf2 ~/SoundFonts/arachno.sf2 --gain 0.45 --reverb 0 --chorus 0 --poly 768 \
  --out augurs_punishing_ostinato_dry
```

---

## "the most complex thing you can do" — insane_interrupters_allmeters

> Comment in original: *"when I asked for 'the most complex thing you can do' /
> now its good after tweaking a lot."* The full command has ~100 perc-interrupter
> patterns (additive/subtractive fill ladders). Recoverable in full from git
> history (`misc/scratch2`). Core idea:

```bash
./play_music \
  --seconds 200 --bpm 220 --instrument saw --mode ostinato \
  --keys 'Abm,G,F#m,Gm,G, Ab,G,Gm,F#m,G, Abm,G,  Ebm,D,C#m,Dm,D, Eb,D,Dm,C#m,D,Ebm,D,  E,Eb,D,Ebm,Eb, E,Eb,Db,Ebm,Eb,  G,Abm,G,F#m,Gm,G,  C,Bbm,Bb,Ebm,Ab,D,G,  Bbm,Bb,Bbm,Bb,  Ebm,Eb,Ebm,Eb,Ebm,Eb,  G,Abm,G,F#m,Gm,G' \
  --chords sevenths sevenths sevenths ninths ninths extended-chords extended-chords lyd-dom sus add6 \
  --chords-order random --chord-len e --chord-fill-rate 0.01 \
  --perc-main 'ebg,eg,eg,ecg,ebg,ecg, ebg,eg,ecg,eg,ebg,eg' \
  --perc-fill-rate 0.38 --poly 1024 \
  --out insane_interrupters_allmeters_dry
  # (chord-interrupters + ~100 perc-interrupters elided — see git history)
```

---

## evolving_three_act — 10-min chromatic journey

```bash
./play_music \
  --seconds 600 --bpm 132 --instrument saw --mode ostinato \
  --keys 'G,Gm,F#m,G,F,Gb,Fm,E, Eb,Ebm,D,Db,Dm,C, B,Bbm,B, Bb,Abm,Ab,A,Bb,B, C,C#,D,Eb,E,Ebm,F, G,Gm,Em,Eb,Ebm,Cm,C, Ab,Abm,Fm,F,E,Eb, Db,Dbm,Bbm,Bb,Bm,B, Gm,G,Am,A,Bb,Bbm,Abm,Ab, G,Cm,F,Bbm,Eb,Abm,Db,Gb,B,E,Am,D,Gm,C,Fm,Bb,Ebm,Ab,Dbm,Gbm,Bm,Em,A,Dm,G,Cm' \
  --chords sevenths ninths extended-chords lyd-dom sus add6 \
  --chords-order random --chord-len e --chord-fill-rate 0.30 \
  --chord-interrupters 'er,ec,er,ec,er,ec' 'ec,er,ec,er,ec,er' 'er,er,ec,er,ec,er' 'ec,er,ec,ec,er,ec' \
  --perc-main 'ebg,eg,ecg,eg,ebg,eg,ecg,eg,ebg,eg,ekh,eg' \
  --perc-interrupters 'eg,ecg,eg,ec,eg,ecg' 'eb,eg,es,et,eu,eg' 'ek,eg,ek,eg,ek,eg' \
  --perc-fill-rate 0.15 --poly 1024 \
  --out evolving_three_act_dry
```

---

## modal_long_sections_drive_clockwork — 10-min, sectioned (from scratch.sh)

A 600s ostinato that writes each chord out 32× to build long static sections
(G maj9 vamp → blocks of sus2add6 / sus4add7 / min11 / majadd6 / min9 …), driven
by a "clockwork" 8th-note groove. Full chart in git history (`misc/scratch.sh`).
Key flags: `--chords extended-chords ninths lyd-dom quartal sus add6 chromatic-mediants`,
`--bpm 132 --chord-length e --chord-fill-rate 0.18`, humanized velocities.
