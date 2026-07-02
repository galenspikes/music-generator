# Percussion letter map

*Reference — the drum-letter alphabet used in percussion tokens (e.g. `qb`, `ebg`,
`qk[vel+10]`). Each letter maps to a General MIDI percussion note. Generated from
`library/percussion_library.json`; do not hand-edit.*

A percussion token is `<duration><letters>[modifiers]`; stacked letters sound
together. `r` = rest. See [token-grammar.md](token-grammar.md) for durations and
the `[prob]`/`[flam]`/`[vel]` modifiers.

| Letter | GM note | Instrument |
|---|---|---|
| `a` | 35 | Acoustic Bass Drum |
| `b` | 36 | Bass Drum 1 |
| `c` | 38 | Acoustic Snare |
| `d` | 40 | Electric Snare |
| `e` | 37 | Side Stick / Rimshot |
| `f` | 39 | Hand Clap |
| `g` | 42 | Closed Hi-Hat |
| `h` | 44 | Pedal Hi-Hat |
| `i` | 46 | Open Hi-Hat |
| `j` | 49 | Crash Cymbal 1 |
| `k` | 51 | Ride Cymbal 1 |
| `l` | 53 | Ride Bell |
| `m` | 57 | Crash Cymbal 2 |
| `n` | 59 | Ride Cymbal 2 |
| `o` | 55 | Splash Cymbal |
| `p` | 52 | Chinese Cymbal |
| `q` | 41 | Low Floor Tom |
| `s` | 45 | Low Tom |
| `t` | 47 | Low-Mid Tom |
| `u` | 48 | Hi-Mid Tom |
| `v` | 50 | High Tom |
| `w` | 54 | Tambourine |
| `x` | 56 | Cowbell |
| `y` | 69 | Cabasa |
| `z` | 70 | Maracas |

*Note:* `r` is a rest (no letter row above). For `--chord-interrupters`,
the letter `c` means "play the chord" and `r` means rest.
