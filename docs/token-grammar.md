# Token grammar reference

The single source of truth for the mini-languages used on the command line.
Behavior here is pinned by `tests/test_tokens.py`.

There are two token languages: **chord tokens** (used by `--keys`) and
**percussion tokens** (used by `--perc-main`, `--perc-interrupters`,
`--chord-interrupters`). Both support the **repetition** and **chain** operators.

---

## 1. Chord tokens (`--keys`)

How `--keys` is interpreted depends on `--mode`:

- `--mode ostinato` → the comma-separated list **is** the progression, looped to
  fill `--seconds`. This is where the token grammar below applies.
- `--mode mixed` / `--mode complete` → `--keys` is **ignored**; the engine walks
  a circle-of-fifths default and chooses chord qualities from `--chords`.

### 1a. Bare roots
A plain note name, optionally minor. Quality comes from `--chords`/`--chords-order`.
- `C`, `G`, `Bb`, `F#`
- Minor marker (`m`/`min`) is **stripped** to a root; sharps are normalized to
  flats: `C#` → `Db`, `F#m` → `Gb`, `Gm` → `G`.

### 1b. Colon tokens — `root[:inversion][:recipe][/bass]`
Full control over a single chord's quality, inversion, and bass.

| Part | Meaning | Default |
|------|---------|---------|
| `root` | note name, e.g. `C`, `Eb`, `F#`, `Am` | required |
| `inversion` | integer; bass = the Nth recipe tone (mod len) | none (root position) |
| `recipe` | a chord-recipe name (see `library/chord_recipes.py`) | `min` if root ends in `m`, else `maj` |
| `/bass` | explicit bass pitch class — **any** note, not just a chord tone | none |

Empty sections are allowed: `A::maj9` (no inversion), `Am::` (minor, default recipe).

Examples:
- `C::maj7` — C major 7
- `Bbm:1:min7` — B♭ minor 7, 1st inversion
- `A::maj9` — A major 9, root position
- `G::maj/C` — G major over a **C pedal** (C is not in the chord)
- `F::7/Eb` — F dominant 7 over E♭ (a slash chord)
- `C:1:maj/G` — explicit `/bass` **overrides** the inversion (bass = G)

Common recipe names: `maj min dim aug 7 maj7 min7 min9 maj9 9 11 13 sus2 sus4
sus4add7 add6 majadd6 maj7add9 min11 quartal` … and many exotic ones. The full
list lives in `library/chord_recipes.py`.

> Slash bass only works **inside a colon token** (`G::maj/C`). A bare `E/A`
> without a colon is not routed to the slash parser.

---

## 2. Percussion tokens (`--perc-main`, `--perc-interrupters`, `--chord-interrupters`)

Form: **`<duration><instrument-letters>[modifiers]`**, comma-separated.

### Durations
| Letter | Beats |
|--------|-------|
| `w` | 4.0 (whole) |
| `h` | 2.0 (half) |
| `q` | 1.0 (quarter) |
| `e` | 0.5 (eighth) |
| `s` | 0.25 (sixteenth) |
| `t` | 0.125 (thirty-second) |

### Instruments
One or more letters after the duration play simultaneously. `r` = rest.
- `qb` — quarter-note kick
- `er` — eighth rest
- `ebg` — eighth-note kick **and** closed hi-hat together
- `ebc` — eighth kick + snare

Drum-letter map (from `library/percussion_library.json`):

| | | | | |
|---|---|---|---|---|
| a Acoustic Bass Drum | b Bass Drum 1 | c Acoustic Snare | d Electric Snare | e Side Stick |
| f Hand Clap | g Closed Hat | h Pedal Hat | i Open Hat | j Crash 1 |
| k Ride 1 | l Ride Bell | m Crash 2 | n Ride 2 | o Splash |
| p China | q Low Floor Tom | s Low Tom | t Low-Mid Tom | u Hi-Mid Tom |
| v High Tom | w Tambourine | x Cowbell | y Cabasa | z Maracas |

(For `--chord-interrupters`, the letter is `c` = "play the chord"; `r` = rest.)

### Per-hit modifiers — `[...]` after a letter
Comma-separated inside the brackets:
- `[vel+N]` / `[vel-N]` — velocity offset (before humanization)
- `[probX]` — play with probability X (0–1, clamped)
- `[flamX]` — add a grace hit X beats later (≥0)

Example: `qk[vel+10,prob0.5]sh` — a quarter with ride (louder, 50% chance),
low tom, and pedal hat.

---

## 3. Repetition & chain operators (both languages)

- **`token*N`** — repeat a token N times: `C::maj*4`, `Am*3`.
- **`[a,b,c]*N`** — repeat a whole group N times: `[C,G]*2` → `C,G,C,G`.
  Inner tokens may carry their own `*N`: `[A:1:maj*2,B::min]*3`.

These let you write long charts compactly, e.g. a 32-bar pedal section as
`G:1:sus2add6*32`.

---

## 4. Melody tokens (`--melody`)

A monophonic line written as **scale degrees** (relative to a key+mode), used by
`--melody` today and the future fugue/lead generators. Whitespace-separated;
`|` barlines are ignored.

Form: **`<duration>[.] ( [#|b]<1-7>['|,]* | r )`**
- **duration**: `w h q e s t` (as above); trailing `.` = dotted (×1.5).
- **degree**: `1`–`7` in the active key/mode.
- **accidental** (before the degree): `#` / `b` — e.g. `#4`, `b7`.
- **octave marks** (after): `'` up, `,` down (repeatable). *(Note: `,` is the
  octave-down mark, so melodies are space-separated, not comma-separated.)*
- **rest**: `r` (e.g. `qr`).
- operators `*N` and `[ ... ]*N` work here too.

Example: `q1 e2 e3 q5 q3 | h2 q1 qr`

The key/mode is **inferred from the chords** (override with `--melody-key` /
`--melody-mode`). Degrees resolve either against the section key
(`--melody-relative key`) or anchored to the current chord's root
(`--melody-relative chord`, so a motif fits each chord). `--melody-transform`
can `invert`/`retrograde`/`augment` the line (the fugal operations).
See docs/melody-primitive-plan.md.
