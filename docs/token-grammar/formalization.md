# Token grammar formalization

*Writing the three token languages precisely: their structure, composition rules, and visual notation.*

---

## Shared primitives

All three languages build on the same foundation:

### Duration (from `DUR_MAP`)
| Symbol | Beats | Seconds @120bpm |
|--------|-------|-----------------|
| `w` | 4.0 | 2.0 |
| `h` | 2.0 | 1.0 |
| `q` | 1.0 | 0.5 |
| `e` | 0.5 | 0.25 |
| `s` | 0.25 | 0.125 |
| `t` | 0.125 | 0.0625 |

**Dotted notation:** `duration.` = duration × 1.5. Examples: `q.` = 1.5 beats, `e.` = 0.75 beats.

### Repetition & grouping
- `token*N` — repeat token N times: `C*4` → `C,C,C,C`
- `[a,b,c]*N` — repeat group N times: `[C,G]*2` → `C,G,C,G`
- Inner tokens may carry their own `*M`: `[C*2,G]*3` → `C,C,G,C,C,G,C,C,G`

---

## 1. Chord tokens (`--keys`)

### Grammar (EBNF-ish)

```
chord_sequence ::= chord (',' chord)*
chord           ::= bare_root | colon_token
bare_root       ::= root [('m' | 'min')]
colon_token     ::= root [':' inversion] [':' recipe] ['/'] [bass]
root            ::= note_name
note_name       ::= ('A'..'G') ['#' | 'b']
inversion       ::= ('0'..'9')+ 
recipe          ::= recipe_name (see chord_recipes.py)
bass            ::= note_name
```

### Examples with breakdown

| Token | Interpretation | Notes |
|-------|---|---|
| `C` | C major triad (from default recipe) | Quality chosen by `--chords-order` |
| `Am` | A minor | Minor is marked; quality inferred |
| `C::maj7` | C major 7, root position | Explicit recipe, no inversion |
| `Bbm:1:min7` | B♭ minor 7, first inversion | Bass = 2nd tone of recipe |
| `G::maj/C` | G major with C in bass | `/C` is explicit bass (not a chord tone) |
| `F:1:7/Eb` | F7, but first inversion's bass is overridden to Eb | `/bass` overrides inversion |

### Parsing rules

1. **Bare root handling:** `C#` → normalize to `Db`; `Am` → strip `m`, use root only
2. **Recipe fallback:** No recipe? Use `maj` unless root ends in `m`, then `min`
3. **Inversion arithmetic:** Inversion `N` means "the Nth tone of the recipe goes in the bass" (mod recipe length)
4. **Bass override:** Explicit `/bass` always wins over inversion

---

## 2. Percussion tokens

### Grammar

```
perc_sequence     ::= perc_hit (',' perc_hit)*
perc_hit          ::= duration instruments [modifiers]
duration          ::= ('w'|'h'|'q'|'e'|'s'|'t') ['.']
instruments       ::= instrument_letter+
instrument_letter ::= ('a'..'z') | 'r'  (r = rest)
modifiers         ::= modifier (',' modifier)*
modifier          ::= '[' modifier_expr ']'
modifier_expr     ::= 'vel' ('+' | '-') digit+ 
                    | 'prob' ('0'|'1'|'0.N')
                    | 'flam' ('0'|'1'|'0.N')
```

### Instrument letters (percussion library)

```
a=Acoustic Bass Drum    b=Bass Drum 1         c=Acoustic Snare    d=Electric Snare
e=Side Stick            f=Hand Clap           g=Closed Hat        h=Pedal Hat
i=Open Hat              j=Crash 1             k=Ride 1            l=Ride Bell
m=Crash 2               n=Ride 2              o=Splash            p=China
q=Low Floor Tom         s=Low Tom             t=Low-Mid Tom       u=Hi-Mid Tom
v=High Tom              w=Tambourine          x=Cowbell           y=Cabasa
z=Maracas               r=Rest (silence)
```

### Examples

| Token | Plays |
|-------|-------|
| `qb` | Quarter-note kick |
| `ebg` | Eighth-note kick AND closed hat (simultaneous) |
| `sr` | Sixteenth rest |
| `qk[vel+10]` | Quarter ride, 10 units louder |
| `qb[prob0.5]` | Quarter kick, plays 50% of the time |
| `qk[vel+10,prob0.5,flam0.125]` | Quarter ride, louder, 50% chance, grace note 1/8 beat early |

---

## 3. Melody tokens

### Grammar

```
melody_sequence  ::= melody_token (space melody_token)*
melody_token     ::= duration ['.'] (pitch | 'r')
duration         ::= ('w'|'h'|'q'|'e'|'s'|'t')
pitch            ::= [accidental] degree [octave_marks]
accidental       ::= '#' | 'b'
degree           ::= ('1'..'7')
octave_marks     ::= ("'" | ',')*
barline          ::= '|'  (allowed, ignored)
```

### Interpretation

- **Degrees** resolve to scale degrees in the active key/mode (inferred from chord context)
- **Accidentals** allow chromatic inflection: `#4` = raised 4th, `b7` = lowered 7th
- **Octave marks:** `'` = up one octave (repeatable), `,` = down one octave
- **Rest:** `r` followed by duration = silence

### Examples

| Token | Meaning |
|-------|---------|
| `q1` | Quarter-note scale degree 1 |
| `e2 e3` | Two eighths: degrees 2 and 3 |
| `q#4` | Quarter-note raised 4th (e.g. F# in C major) |
| `h1,,` | Half-note degree 1, two octaves below |
| `q.' e5` | Dotted-quarter degree 1, then eighth degree 5 |
| `qr` | Quarter rest |
| `q1*4` | Four quarter-note 1's in a row |

---

## Visual notation

### Mock-up: score representation

A token can be drawn as a score:

```
Chord:  C::maj7
Perc:   qb, eg, qk
Melody: e1 e2 e3 | q5 h3

Score staff:
  ♪ ♪ ♪ |  ♩  𝅗𝅥
  C: maj7
  Bass: ♩  Closed-Hat: ♪
```

### Linear representation (for this document)

Tokens are written in plain text:
- **Chord:** `C::maj7`
- **Percussion:** `qb, eg, qk`
- **Melody:** `e1 e2 e3 | q5 h3`

Future: SVG/graphical notation for the webapp.

---

## Transforms (melody only)

The melody language includes transforms for fugal operations. These are applied *at the degree level* before realization to MIDI.

| Transform | Effect | Example |
|-----------|--------|---------|
| `invert` | Mirror degrees about an axis | `invert[q1 e2 e3]` |
| `retrograde` | Reverse the order | `retrograde[q1 e2 e3]` |
| `augment:factor` | Multiply durations | `augment:2[q1 e2]` → `h1 q2` |
| `shift:degree` | Transpose to start on a new degree | `shift:5[q1 e2 e3]` (TBD syntax) |

---

## Open questions

1. **Voice assignment notation** — how to write "soprano gets this, alto gets that"? Options:
   - `[S:melody] [A:melody]` — per-voice labels
   - `S{...} A{...}` — block notation
   - Separate tokens per voice: `--melody-soprano`, `--melody-alto`, etc.

2. **Stretto (time offset)** — how to express "voice B enters 0.5 beats after voice A"?
   - `[at:0.0]melody1 [at:0.5]melody2` ?
   - Or a higher-level "fugue entry" construct?

3. **Harmonic anchoring** — how to bind a melody to specific chord positions? Currently implicit; could be explicit:
   - `melody=[root|fifth|third]` (anchor the melody to that degree of the chord)

4. **Duration alias** — should there be shorthand for common rhythmic patterns?
   - E.g. `triplet` = three equal notes in the space of two?
   - Or is that overloading the DSL?

---

## See also

- [Barber fugue study](barber-fugue-study.md) — what the grammar needs to handle
- [Living musical ideas](living-musical-ideas.md) — the semantic level
- [Reference token grammar](../reference/token-grammar.md) — the canonical, test-pinned spec
