# Living musical ideas

*What does it mean for a musical idea to be "living" in the token system? When is a token representation *alive* — capturing intent, allowing variation, suggesting development — versus dead (a mere transcription)?*

---

## The question

A "dead" token representation:
- Transcribes a finished piece exactly
- Specifies every note, every duration, every articulation
- Leaves nothing to the engine; the engine just renders it
- Has no generative power; play it again → identical output

A "living" token representation:
- Captures the *identity* of a musical idea (its essence, not its details)
- Allows the engine to *realize* it in context (adapt to harmony, key, register)
- Generates *variations* that feel true to the original
- Grows when used — the idea unfolds, doesn't repeat

---

## Examples

### Living: the chord

```
C::maj7
```

This token says "a C major 7th chord" — but not:
- Which octave
- Which inversion (we assume root position, but the engine can voice-lead)
- Which instruments play it
- Which velocity
- How long it sustains

The token is **instructions for a category of sound**, not a specific sound. The engine can realize it as a block, or voice-lead from the previous chord, or pass it to different instruments. Each realization is alive with the same intent.

### Dead: the block

```
MIDI note-ons: C3, E3, G3, B3 @ velocity 64, duration 480 ticks
```

This is the same chord, but *specified to death*. There's nothing left for the engine to do but play it.

### Living: the fugue subject

```
q1 e2 e3 | q5 q6 q7 | h1
```

This melody says: "a scalar ascent with a specific rhythm, starting on the tonic." It's alive because:
- It can transpose (the token stays the same; the key context changes)
- It can invert (the degrees flip about an axis, preserving the shape)
- It can augment (the rhythm stretches, the shape persists)
- It can appear in any voice, any register, against any harmonic background

The token captures the *idea* (scalar ascent, tonic → dominant), not the realization.

### Dead: the transcription

```
MIDI: C4 D4 E4 | G4 A4 B4 | C5
```

The same melody, but locked to one octave, one key, one realization. The token is a recording, not an idea.

---

## Criteria for "living"

A token representation is living if it:

1. **Captures identity** — a listener would recognize the idea even if realized differently
2. **Is mode-invariant** — the idea is understood relative to tonality, not absolute pitch
3. **Is reversible** — you could hear the realized version and reconstruct the intent
4. **Allows transformation** — inversion, retrograde, transposition, rhythm-scaling all preserve the idea
5. **Suggests development** — the token hints at how the idea could grow (motif recombination, augmentation, variation)
6. **Is decoupled from instrumentation** — the idea is independent of which instrument plays it
7. **Is sparse** — it specifies the essential features, not every detail

---

## Analysis: the three languages

### Chord tokens

| Aspect | Living? | Why |
|--------|---------|-----|
| **Identity** | ✅ | `C::maj7` means "this exact chord quality" |
| **Tonality** | ✅ | The token is tonal (a named chord, not MIDI numbers) |
| **Transformation** | ⚠️ | You can invert, but the token doesn't guide it |
| **Development** | ⚠️ | A chord token is static; progressions are sequences |
| **Instrumentation** | ⚠️ | The token doesn't specify voice allocation |
| **Sparsity** | ✅ | Just the root, quality, inversion, bass |

**Overall:** Chord tokens are alive in the harmonic dimension (tonality, quality). They are less alive in the voice/register dimension (no explicit allocation).

### Percussion tokens

| Aspect | Living? | Why |
|--------|---------|-----|
| **Identity** | ⚠️ | `ebg` is "eighth kick + closed hat," but is that a *motif* or just a sound? |
| **Tonality** | ❌ | Percussion is pitch-independent (drumming, cymbals) |
| **Transformation** | ❌ | Invert a drum pattern? Retrograde it? Semantically murky |
| **Development** | ❌ | Patterns don't evolve; they repeat or mutate stochastically |
| **Instrumentation** | ⚠️ | The token specifies instruments but not voice/hand |
| **Sparsity** | ✅ | Just duration and which drums play |

**Overall:** Percussion tokens are rhythmic motifs, not harmonic/tonal ones. They're alive *as texture* but not as *developing ideas*. The engine can vary fill_rate and velocity, but the pattern itself doesn't transform.

**Question:** Is a drum pattern a "living idea" or just a groove? Maybe the answer depends on intent. A kick-snare pattern could be a motif if you're thinking of it as "the statement"; it's just texture if it's background.

### Melody tokens

| Aspect | Living? | Why |
|--------|---------|-----|
| **Identity** | ✅ | The degree sequence captures the shape |
| **Tonality** | ✅ | Degrees are tonal; inferred key/mode context |
| **Transformation** | ✅ | Invert, retrograde, augment all work on degrees |
| **Development** | ✅ | The token is a motif; transposition + transformation = development |
| **Instrumentation** | ⚠️ | The token doesn't specify which voice; engine assigns |
| **Sparsity** | ✅ | Just durations and degrees; register is post-hoc |

**Overall:** Melody tokens are the most alive. They capture *musical form* (motif, subject, response). The degree-based representation enables fugal operations.

---

## The hierarchy of aliveness

```
Dead (transcription) ← → Living (idea)
  ↓
- MIDI numbers (pitch-locked)
- Absolute rhythms (tempo-locked)
- Specified voices (no reallocation)
- Realized dynamics (no humanization)
  ↓
- Chord tokens (harmonic identity, but static)
- Drum patterns (rhythmic identity, but non-transformable)
  ↓
- Melody tokens (degree-based, fully transformable)
- Harmonic progressions (tonal motion as a shape)
  ↓
- Rule-based generation (no single source, infinite variations)
```

The token system aims for the *upper-middle*: specific enough to express a composed idea, abstract enough to allow realization and transformation.

---

## What would make the system more "living"?

1. **Multi-voice melodic ideas** — a fugue subject is one voice, but a "musical idea" might be two or more voices simultaneously (subject + countersubject). The token system would need voice-assignment notation.

2. **Harmonic intention** — currently melody is "adapted to the chords," but what if the token could express "this melody should resolve to the fifth of the chord"? That would make melody-harmony relationships explicit and alive.

3. **Development primitives** — beyond invert/retrograde, the token could express "compress this motif by half," "interlock two motifs," "invert and compress together." These are the *operations* composers use to develop.

4. **Pedagogical sparsity** — a living token should be learnable by ear and by eye. `q1 e2 e3 | q5` should be singable without looking at a staff. Drum patterns should be countable by hand. Chords should be voiceable without calculation.

5. **Contextual realization** — the token should say "in this context, *sound like this," not "always sound exactly like this." Adaptation to context = life.

---

## Case study: the Barber subject

The fugue subject (a musical idea):

```
Degrees (key-relative):  1  2  3  5  6  7  1
Rhythm:                  e. e  q  q  e  e  q
Combined token:          e.1 e2 q3 | q5 e6 e7 | q1
```

This is alive because:
- ✅ It's recognizable (scalar ascent, rhythmic profile)
- ✅ It can transpose (change key, token stays the same)
- ✅ It can invert (degrees flip, shape persists)
- ✅ It can augment (rhythm stretches)
- ✅ It can appear in any voice

It would be more alive if:
- ⚠️ The token could express "tonal answer on degree 5" (not just "transpose"; the *function* of the answer)
- ⚠️ The token could express "when the answer comes in, voice B plays this countersubject"
- ⚠️ The token could express "this subject in stretto (accelerated entry)"

---

## See also

- [Barber fugue study](barber-fugue-study.md) — a living musical idea in practice
- [Formalization](formalization.md) — the grammar that enables aliveness
- [Design philosophy: stasis](../explanation/stasis-and-function.md) — the broader musical thinking
