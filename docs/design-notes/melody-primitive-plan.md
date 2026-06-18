# Melody primitive — design plan

Status: **v1 shipped** — `melody.py` (parser, scales, `infer_key`,
`realize_melody` key+chord-relative, transforms) with `tests/test_melody.py`,
auditionable via `--melody` on the soprano voice. v2 (tonal answer, chord-tone
anchoring, ties) and the generators (fugue/lead) build on it.

A small **melody mini-language** + parsed model + transforms that serves as
shared foundation for:
- **fugue subjects** (a theme that gets answered, inverted, stretto'd), and
- the **lead/hook generator** (state a motif, then develop it).

It extends the existing token DSL from *rhythm-only* (percussion) to *pitched*,
in the same house style (duration prefix, `r` rest, `*N` repeat, `[...]*N`
chain).

---

## 1. Pitch representation — **scale degrees** (the key decision)

Three options were considered:
- **Absolute notes** (`C4 E4 G4`): simple, but key-dependent; diatonic
  transposition (the fugal *answer*) and inversion are awkward.
- **Intervals** (relative steps): good for transpose, clumsy for inversion/
  retrograde and for reading.
- **Scale degrees** (`1 3 5`, relative to a key + mode): ← **chosen.**

Degrees win because every operation a fugue needs is a clean transform on
degrees: the **answer** is a diatonic shift, **inversion** is a reflection of
degrees about an axis, **augmentation** scales durations — all key-independent.
Realization to MIDI happens later, given a key/mode/register.

---

## 2. The melody token grammar

A melody is comma- *or* space-separated tokens. Each token:

```
<duration>[.] ( [accidental] <degree> [octave-marks] | r )
```

- **duration**: reuse `DUR_MAP` — `w h q e s t` (whole … 32nd). Optional
  trailing `.` = dotted (×1.5).
- **degree**: `1`–`7` (relative to the section/song key + mode).
- **accidental** (before the degree, roman-numeral style): `#` or `b`
  (e.g. `#4`, `b7` — lets you spell harmonic minor's raised 7 explicitly).
- **octave-marks** (after): `'` up an octave, `,` down (repeatable: `''`).
- **rest**: `r` (e.g. `qr`, `hr`).
- **barlines**: `|` allowed and ignored (readability only).

### Examples
```
# a subject in the section's key/mode
q1 q5 e5 e4 q3 | h2 q1 qr

# dotted rhythm, octave leaps, a raised 7th
q.1 e5 q3' e#7, h1

# operators carry over from the DSL
[q1 q3 q5]*2, h1          # repeat a cell
```

Monophonic by design (one note per token) — fugal voices and a lead are single
lines.

---

## 3. Parsed model

```python
@dataclass(frozen=True)
class MelodyNote:
    degree: int | None     # 1..7, or None for a rest
    accidental: int        # -1, 0, +1
    octave: int            # relative octave offset (… -1, 0, +1 …)
    beats: float           # from duration (+ dot)
    is_rest: bool
```
`parse_melody(text) -> list[MelodyNote]` (mirrors `parse_pattern`). Golden tests
like the rest of the DSL.

---

## 4. Scales / modes (new, small)

Degrees need a scale. Add a tiny table (interval sets from the tonic):
```
major/ionian:  [0,2,4,5,7,9,11]
minor/aeolian: [0,2,3,5,7,8,10]
dorian:        [0,2,3,5,7,9,10]
mixolydian:    [0,2,4,5,7,9,10]
... (phrygian, lydian, locrian, harmonic/melodic minor)
```
`degree_to_pc(degree, accidental, mode) -> pitch class offset`. (Harmonic-minor
colour can also just be spelled with `#7` explicitly.)

---

## 4b. Key/scale inference from chords  *(decided: derive from the chords)*

Degrees resolve against a key+mode that we **infer from the section's chord
progression** rather than requiring the user to declare it.

```python
infer_key(chord_seq) -> (tonic_pc, mode)
```
Heuristic:
1. Tally pitch classes across the section's chords (weight by duration/count).
2. Score each (tonic, mode) candidate by how well its scale covers those pcs
   (penalize out-of-scale tones), across all 12 roots and the mode table.
3. Break ties with tonic cues: the final chord root, the most frequent root,
   and root-position emphasis.

**An explicit `key:`/`mode:` override is always allowed** as a safety valve —
inference will mis-guess on modal/chromatic charts, so the override stays.

## 5. Realization to MIDI  *(decided: support key- and chord-relative)*

```python
realize_melody(notes, key_pc, mode, base_octave, lo, hi,
               relative="key", chord_tl=None)
    -> list[(beat_offset, dur, midi_note)]
```
- `relative="key"` — degree resolves against the inferred section scale
  (constant). Correct for fugue subjects and stable melodies.
- `relative="chord"` — degree is anchored to the **current chord's root** at the
  note's time (walk `chord_tl`); the section scale still supplies the steps, so a
  motif **diatonically transposes to fit each chord**. Great for hooks over
  changes. (A later refinement: chord-*tone* anchoring, where 1/3/5/7 land on
  actual chord tones.)

Either way it emits the same `(when, dur, note)` shape `build_bass_line` already
produces, so it drops straight into the event pipeline.

---

## 6. Transformations (what makes fugue + development possible)

Pure functions on `list[MelodyNote]` (degree representation makes them trivial):

- `transpose_diatonic(m, steps)` — shift each degree by N scale steps (octave
  wrap). The fugal **answer** = transpose up a 4th/5th. *Real* answer = exact
  interval; *tonal* answer = special-case the opening 1↔5 (v2).
- `transpose_chromatic(m, semitones)` — for modulation / real answers.
- `invert(m, axis_degree)` — reflect degrees about an axis (melodic inversion).
- `retrograde(m)` — reverse the note order.
- `augment(m, factor)` / `diminish(m, factor)` — scale all durations (stretto &
  development).

These are exactly the operations the fugue mode and the lead developer call.

---

## 7. How the two consumers use it

**Fugue mode** (future): subject = a parsed melody; answer =
`transpose_diatonic(subject, +4)`; countersubject = a second melody; episodes =
`retrograde`/sequence of subject fragments; stretto = overlapping entries via
time offsets; each voice → its own channel (already supported). Voiced with
`realize_melody` per voice register.

**Lead/hook generator** (Thread 2): either you **hand-write** a hook in this
language, or the generator **emits** `MelodyNote` lists (chord-tone biased) and
**develops** them with the same transforms. Realized onto a lead channel.

---

## 8. Surface (YAML / CLI)

Hand-written melody as a lead, per section:
```yaml
lead:
  instrument: sax
  melody: "q1 q5 e5 e4 q3 | h2 q1 qr"
  octave: 5          # register anchor
# key/mode come from the section (see open questions)
```
Fugue (later): `subject:` uses the same string.

A standalone `--melody "..."` flag could also play a single line for quick
audition.

---

## 9. Phasing
- **v1:** grammar + `parse_melody` + model + scales + `realize_melody` +
  `transpose_diatonic`/`invert`/`retrograde`/`augment`. Golden tests. Wire a
  hand-written melody onto a voice so we can *hear* a line and its inversion.
- **v2:** tonal answer, chord-relative degree mode (for leads over changes),
  ties (`~`) and slurs.
- **v3:** the generators on top (fugue mode; motif developer).

---

## 10. Decisions & remaining questions

**Decided:**
- Pitch = **scale degrees** (§1).
- Key/mode is **inferred from the chords** (§4b), with an explicit override kept.
- Realization **supports both** key-relative and chord-relative degrees via a
  flag (§5).
- Accidental **before** the degree (`#4`); **octave marks** (`'`/`,`); **ties
  deferred** to v2.

**Still open (smaller):**
1. **Chord-relative semantics:** v1 anchors degrees to the chord *root* and uses
   the section scale for steps (diatonic transposition of the motif). Later:
   chord-*tone* anchoring (1/3/5/7 = actual chord tones). OK to start root-based?
2. **Inference scope for v1:** which mode set to score against — start with
   {major, natural minor, dorian, mixolydian} and expand? (Smaller set = fewer
   mis-guesses.)
3. **Default `relative` per consumer:** fugue subjects → `key`; lead/hook →
   `chord`. Sensible defaults so most specs don't set the flag?

## 11. Revised component list / sequencing (v1)
1. `parse_melody` + `MelodyNote` model + grammar (golden tests).
2. Scales/modes table + `degree_to_pc`.
3. `infer_key(chord_seq)` (+ explicit override) — **new prerequisite** from the
   "derive from chords" decision; the trickiest, most ear-checked piece.
4. `realize_melody(..., relative=, chord_tl=)` (key- and chord-relative).
5. Transforms: `transpose_diatonic`, `invert`, `retrograde`, `augment`.
6. Wire a hand-written `--melody` onto a voice to audition a line + its
   inversion (proves the whole chain before generators are built).
