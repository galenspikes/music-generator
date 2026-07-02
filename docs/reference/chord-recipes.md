# Chord-recipe catalog

*Reference — every named chord recipe usable in the `:recipe` slot of a colon
chord token (e.g. `C::maj7`, `Bb:1:min9`). Generated from `library/chord_recipes.py`; do not hand-edit.*

There are **81 recipes**. Each lists the semitone offsets from the
root and the resulting pitch classes voiced from C. See [token-grammar.md](token-grammar.md) for how recipes combine with roots,
inversions, and slash bass.

| Recipe | Intervals (semitones) | Pitch classes from C |
|---|---|---|
| `maj` | 0, 4, 7 | C E G |
| `min` | 0, 3, 7 | C Eb G |
| `dim` | 0, 3, 6 | C Eb Gb |
| `aug` | 0, 4, 8 | C E Ab |
| `7` | 0, 4, 7, 10 | C E G Bb |
| `maj7` | 0, 4, 7, 11 | C E G B |
| `min7` | 0, 3, 7, 10 | C Eb G Bb |
| `mmaj7` | 0, 3, 7, 11 | C Eb G B |
| `hdim7` | 0, 3, 6, 10 | C Eb Gb Bb |
| `m7b5` | 0, 3, 6, 10 | C Eb Gb Bb |
| `wdim7` | 0, 3, 6, 9 | C Eb Gb A |
| `dim7` | 0, 3, 6, 9 | C Eb Gb A |
| `sus2` | 0, 2, 7 | C D G |
| `sus4` | 0, 5, 7 | C F G |
| `sus2add7` | 0, 2, 7, 10 | C D G Bb |
| `sus4add7` | 0, 5, 7, 10 | C F G Bb |
| `majadd6` | 0, 4, 7, 9 | C E G A |
| `majadd9` | 0, 4, 7, 14 | C E G D |
| `majaddb9` | 0, 4, 7, 13 | C E G Db |
| `majadd#9` | 0, 4, 7, 15 | C E G Eb |
| `majadd11` | 0, 4, 7, 17 | C E G F |
| `majadd#11` | 0, 4, 7, 18 | C E G Gb |
| `majaddb13` | 0, 4, 7, 20 | C E G Ab |
| `majadd13` | 0, 4, 7, 21 | C E G A |
| `maj7add9` | 0, 4, 7, 11, 14 | C E G B D |
| `minadd6` | 0, 3, 7, 9 | C Eb G A |
| `minadd9` | 0, 3, 7, 14 | C Eb G D |
| `minadd11` | 0, 3, 7, 17 | C Eb G F |
| `9` | 0, 4, 7, 10, 14 | C E G Bb D |
| `maj9` | 0, 4, 7, 11, 14 | C E G B D |
| `min9` | 0, 3, 7, 10, 14 | C Eb G Bb D |
| `11` | 0, 4, 7, 10, 14, 17 | C E G Bb D F |
| `13` | 0, 4, 7, 10, 14, 21 | C E G Bb D A |
| `min11` | 0, 3, 7, 10, 14, 17 | C Eb G Bb D F |
| `min13` | 0, 3, 7, 10, 14, 21 | C Eb G Bb D A |
| `7b5` | 0, 4, 6, 10 | C E Gb Bb |
| `7#5` | 0, 4, 8, 10 | C E Ab Bb |
| `7b9` | 0, 4, 7, 10, 13 | C E G Bb Db |
| `7#9` | 0, 4, 7, 10, 15 | C E G Bb Eb |
| `7b11` | 0, 4, 7, 10, 16 | C E G Bb E |
| `7#11` | 0, 4, 7, 10, 18 | C E G Bb Gb |
| `7b13` | 0, 4, 7, 10, 20 | C E G Bb Ab |
| `7#13` | 0, 4, 7, 10, 22 | C E G Bb Bb |
| `7alt` | 0, 4, 6, 8, 10, 13, 15 | C E Gb Ab Bb Db Eb |
| `split3` | 0, 3, 4, 7 | C Eb E G |
| `maj7split3` | 0, 3, 4, 7, 11 | C Eb E G B |
| `7split3` | 0, 3, 4, 7, 10 | C Eb E G Bb |
| `5` | 0, 7 | C G |
| `5add8` | 0, 7, 12 | C G C |
| `5add9` | 0, 7, 14 | C G D |
| `it6` | 0, 4, 10 | C E Bb |
| `fr6` | 0, 4, 6, 10 | C E Gb Bb |
| `ger6` | 0, 3, 4, 10 | C Eb E Bb |
| `n6` | 0, 4, 8 | C E Ab |
| `quartal` | 0, 5, 10 | C F Bb |
| `quartal7` | 0, 5, 10, 15 | C F Bb Eb |
| `quintal` | 0, 7, 14 | C G D |
| `so_what` | 0, 5, 10, 15, 20 | C F Bb Eb Ab |
| `lydian_stack` | 0, 4, 6, 11 | C E Gb B |
| `tristan` | 0, 6, 10, 15 | C Gb Bb Eb |
| `mystic` | 0, 2, 4, 6, 9, 10 | C D E Gb A Bb |
| `whole_tone` | 0, 2, 4, 6, 8, 10 | C D E Gb Ab Bb |
| `petrushka` | 0, 1, 4, 7 | C Db E G |
| `augurs` | 0, 1, 7, 8 | C Db G Ab |
| `messiaen_resonance` | 0, 4, 7, 10, 14, 18, 21 | C E G Bb D Gb A |
| `messiaen_resonance_pc` | 0, 4, 7, 10, 2, 6, 9 | C E G Bb D Gb A |
| `messiaen_dom` | 0, 2, 4, 6, 9, 10 | C D E Gb A Bb |
| `tone_cluster_3` | 0, 1, 2 | C Db D |
| `tone_cluster_4` | 0, 1, 2, 3 | C Db D Eb |
| `tone_cluster_5` | 0, 1, 2, 3, 4 | C Db D Eb E |
| `chromatic_cluster` | 0, 1, 2, 3, 4 | C Db D Eb E |
| `diatonic_cluster` | 0, 2, 4, 5, 7 | C D E F G |
| `bartok` | 0, 3, 6, 9 | C Eb Gb A |
| `octatonic_tet` | 0, 3, 6, 9 | C Eb Gb A |
| `wholetone_tet` | 0, 2, 4, 6 | C D E Gb |
| `add4` | 0, 4, 5, 7 | C E F G |
| `sus2add6` | 0, 2, 7, 9 | C D G A |
| `maj7#11` | 0, 4, 7, 11, 18 | C E G B Gb |
| `min7#11` | 0, 3, 7, 10, 18 | C Eb G Bb Gb |
| `min7add9` | 0, 3, 7, 10, 14 | C Eb G Bb D |
| `lyd-dom` | 0, 4, 6, 10 | C E Gb Bb |
