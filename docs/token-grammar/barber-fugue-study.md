# Case study: Barber's Piano Sonata, Op. 26, III (Fugue)

*A test of the token system's expressive power. Can we represent the fugue from Barber's Piano Sonata? What does it require? What would need to exist in the token system to make it possible?*

---

## The question

The Barber fugue is a substantial, sophisticated polyphonic form:
- A clear subject with a recognizable shape (scalar, rhythmic, intervallic identity)
- An answer (transposed, tonally adjusted)
- Multiple countersubjects
- Stretto (accelerated subject entries, overlapping)
- Inversion of the subject
- A development section with tonal motion
- A final recapitulation

**Can the token system represent this in a way that:**
1. Feels like *composing* the fugue (not transcribing MIDI)
2. Captures the *intent* — the subject, the answer, the transforms
3. Allows the engine to *realize* it (render to voices/harmony)
4. Produces output recognizably in conversation with Barber's original

---

## What the token system has

| Feature | Chord | Percussion | Melody | Status |
|---------|-------|-----------|--------|--------|
| **Pitch representation** | ✓ (chords) | ✗ | ✓ (scale degrees) | Melody: degrees chosen for fugal transforms |
| **Duration** | implicit (chord_len) | ✓ | ✓ | Unified in DUR_MAP |
| **Repetition `*N`** | ✓ | ✓ | ✓ | Works in all three |
| **Transforms (invert/retrograde/augment)** | ✗ | ✗ | ✓ (melody only) | Melody.py has `transform()` |
| **Tonal answer (diatonic shift)** | ✗ | ✗ | ✓ (melody.py) | Melody: degrees let answer be a shift |
| **Stretto (rhythmic acceleration)** | ✗ | ✗ | ? | Melody dotted notation exists; compaction? |
| **Counterpoint (multiple voices)** | ? | ✗ | ? | Melody is monophonic; harmony is generative |
| **Explicit voice layout** | ✗ | ✗ | ✗ | Engine voice-leads; no "this goes to soprano" |
| **Tonal motion / modulation** | implied by chords | ✗ | inferred from chord context | No explicit pivot plan |
| **Polyphonic articulation** | ✗ | ✗ | ✗ | No cross-voice synchronization |

---

## The Barber subject

The fugue subject is a scalar idea with strong rhythmic profile. In scale degrees (C major, for simplicity):

```
e5. e4 e4 | q1 e2 e3 | q5 e6 e7 | q1 hr (implied pause)
```

*Rough approximation: dotted-eighth E E, quarter C, eighths D E, quarter G, eighths A B, quarter C, half rest.*

In the current melody token format:

```
e.5 e5 e4 | q1 e2 e3 | q5 e6 e7 | q1 hr
```

**Works.** The subject is representable.

---

## The tonal answer

The answer in classical fugue is transposed and tonally adjusted. In the key of C, the subject begins on scale degree 1 (the tonic); the answer typically begins on scale degree 5 (the dominant).

Current state: **Melody.py can shift a motif to a new degree.** If the subject is `[e.5 e5 e4, q1 e2 e3, ...]`, we can ask for a transposed version starting on degree 5. But the current `--melody-transform` interface doesn't expose this yet — it's designed into the code, not into the token grammar.

**Requirement:** The token grammar needs a way to say "the answer is the subject starting on degree 5" — maybe:
```
subject = [q1 e2 e3 ...]
answer = subject@5  (start on degree 5, diatonic shift)
```

Or more explicitly:
```
answer = [shift:5]q1 e2 e3 ...
```

---

## Multiple voices at once

The fugue has 4 voices (S, A, T, B). The subject enters in one voice, then another, then another. During the answer, a countersubject plays against it in a different voice.

**Current state:** The melody token is monophonic (one line at a time). The harmony is generative (voice-led). There is **no way to say "soprano gets this, alto gets that, tenor gets that"** — no explicit voice assignment.

**Requirement:** Some way to specify which voice(s) get which melody. Options:
- `[S:q1 e2 e3], [A:q5 e6 e7]` — explicit voice labels
- Or rely on separate `--melody-soprano`, `--melody-alto`, etc. flags
- Or a more sophisticated notation that lets you write voices stacked

---

## Stretto (compression + overlap)

In the stretto, subject entries come closer together — sometimes the second voice enters before the first has finished. The token system would need to express:
1. Time offset for each voice entry
2. Perhaps a compressed/augmented version of the subject

**Current state:** No time-offset notation. Melody tokens are strictly sequential.

**Requirement:** Something like:
```
[at:0]S:subject, [at:0.5]A:subject, [at:1.0]T:subject, [at:1.5]B:subject
```

---

## Countersubject (against the answer)

While the answer plays in one voice, a countersubject (a second idea) plays in another. They are meant to interlock and have harmonic coherence.

**Current state:** No explicit mechanism to say "these two melodies should play together" and have the engine understand their voice relationship.

**Requirement:** A way to compose counterpoint. Options:
- Explicit voice assignment + simultaneous melody specs
- Or a higher-level "duet" notation that says "melody A and melody B together"

---

## Development & tonal motion

The fugue modulates — it moves through related keys. The token system would need to express:
1. A section in a new key
2. How the harmony supports / anchors the melody in that key

**Current state:** Melody is relative to an inferred key (from chords). If you change the chord progression, the melody reinterprets. This works for key changes — you could specify new chords in a new key and the melody would follow.

**Partial solution:** Specify chords for the development section; the melody interprets relative to them.

---

## What's missing: A fugue notation layer

To truly represent a Barber-like fugue in tokens, we'd need:

1. **Voice assignment** — explicit or implicit marking of which voice gets which line
2. **Timing/offset** — when entries happen, especially for stretto
3. **Tonal answer as a language primitive** — `subject@degree` or `shift:degree` notation
4. **Multi-voice coordination** — a way to say "these voices are simultaneous and interlock"
5. **Harmonic anchoring** — melody + harmony working together, not melody floating free

---

## Could we do it today?

Partially:
- ✅ The subject itself: tokens work
- ✅ The answer as a melodic variant: would require writing it out or adding `shift:degree` syntax
- ✅ Key changes in development: chord changes guide the melody's tonality
- ❌ Explicit 4-voice layout: would need voice assignment notation
- ❌ Stretto entries with timing: would need offset notation
- ❌ Tight counterpoint (countersubject against answer): possible in principle but clunky

**Verdict:** You could *sketch* a Barber-like fugue in tokens. It would require some extensions (voice assignment, tonal answer, stretto timing). The engine would then interpret that sketch and generate the full four-part realization.

---

## Next steps

1. **Write the Barber subject and answer as tokens** — test what works, what breaks
2. **Design voice-assignment notation** — how does "this voice gets this line" look?
3. **Design tonal-answer syntax** — `subject@5` or `[shift:5]` ?
4. **Test a short fugal progression** — S–A–T–B entries with simple countersubject
5. **Measure against the original** — does our interpretation feel like a fugue?
