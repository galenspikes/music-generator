# Kiss On My List (Hall & Oates) — work in progress

Goal: a long-form (20-min) generative groove on this chart.

## Key decisions
- **Capo 3 → rendered at concert (sounding) pitch** (written shape +3 semitones),
  so it matches the record. Mapping used:

  | Written (capo shape) | Concert | Token |
  |---|---|---|
  | A    | C   | `C::maj` |
  | Am   | Cm  | `C::min` |
  | C    | Eb  | `Eb::maj` |
  | D    | F   | `F::maj` |
  | Dm   | Fm  | `F::min` |
  | Dm7  | Fm7 | `F::min7` |
  | Dm9  | Fm9 | `F::min9` |
  | E    | G   | `G::maj` |
  | E7   | G7  | `G::7` |
  | Esus/B | Gsus4 | `G::sus4` |
  | E7sus | G7sus4 | `G::sus4add7` |
  | F    | Ab  | `Ab::maj` |
  | G    | Bb  | `Bb::maj` |
  | Amaj7 | Cmaj7 | `C::maj7` |
  | Dmaj7 | Fmaj7 | `F::maj7` |
  | D7/C  | F7 (top) | `F::7` |
  | Bm7   | Dm7 | `D::min7` |
  | Bm7add11 | Dm7add11 | `D::min11` |

- **Slash chords** (E/A, D/A, G/A, D7/C, D/E, Esus/B): now rendered with a real
  pedal/slash bass via the `/bass` token suffix (e.g. `G::maj/C` = G major over a
  C bass). The chorus rides a concert-C pedal (= the written A-pedal under E/A,
  D/A, G/A). Bass need not be a chord tone.

## Current form (loops in ostinato mode)
Intro → Verse → Pre-chorus → Chorus ×2 → Solo → Chorus.
Pre-chorus #2 variant (uses `D::min11` for Bm7add11) not yet included.

## Render command (90s first pass, with pedal bass)
```bash
KEYS="\
G::maj, C::maj, G::maj, Eb::maj, F::maj, C::maj, \
C::min, F::min7, Ab::maj, Ab::maj/Bb, C::maj, C::min, F::min9, F::min, Ab::maj, Ab::maj/Bb, C::maj, \
F::min7, G::sus4/D, F::min7, G::sus4/D, F::min7, G::sus4/D, F::min7, F::maj/G, G::7, \
G::maj, C::maj, G::maj/C, F::maj/C, G::maj/C, C::min, Bb::maj/C, C::min, F::maj, G::maj/C, C::maj, G::maj/C, C::maj, \
G::maj, C::maj, G::maj/C, F::maj/C, G::maj/C, C::min, Bb::maj/C, C::min, F::maj, G::maj/C, C::maj, G::maj/C, C::maj, \
C::maj7, C::maj7, F::maj7, F::maj7, F::7/Eb, F::7/Eb, G::sus4/D, G::sus4add7, C::maj7, C::maj7, F::maj7, F::maj7, F::7/Eb, F::7/Eb, D::min7, G::sus4add7, \
G::maj, C::maj, G::maj/C, F::maj/C, G::maj/C, C::min, Bb::maj/C, C::min, F::maj, G::maj/C, C::maj, G::maj/C, C::maj"

./play_music --save-wav --no-play \
  --mode ostinato --keys "$KEYS" \
  --chords triads sevenths ninths sus add6 --chords-order roundrobin \
  --bpm 148 --instrument epiano --chord-length h \
  --satb-style arpeggio --counterpoint-step 0.25 \
  --perc-main 'ebg,eg,ecg,eg, ebg,eg,ecg,eg' \
  --perc-interrupters 'ebg,eg,ecg,eg, ebg,eg,ecg,ei' 'sb,sc,sb,sc,sg,sg,sj' \
  --perc-fill-rate 0.18 \
  --sf2 SoundFonts/arachno.sf2 --gain 0.7 --fx lush \
  --normalize --boost-normalize 2 \
  --seconds 90 --out kiss_on_my_list_pedal
```
For the 20-minute version: change `--seconds 90` to `--seconds 1200`.

> Slash-bass syntax: append `/bass` to any colon token — `root[:inv][:recipe]/bass`.
> The bass pitch class can be any note (not just chord tones), so pedals work.
> An explicit `/bass` overrides an inversion.

## TODO / ideas
- Tempo: used 148 bpm (record is ~150-ish). Tune to taste.
- Try `--instrument piano` or `saw` vs `epiano`; try `--satb-style block`.
- ~~Add pedal-bass for the chorus slash chords~~ ✅ done (`/bass` suffix).
- Add the pre-chorus #2 variant with `D::min11`.
- Vary sections over the 20 min (chord-interrupters, fill-rate curve) so it
  evolves rather than loops identically.
