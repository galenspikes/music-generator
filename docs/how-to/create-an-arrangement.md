# How to create an arrangement

*Goal: sequence multiple sections into one evolving piece with a YAML song file.
When `--song` is set, section-based rendering is used and most other flags are
ignored.*

## Render a song

```bash
venv/bin/python music_generator.py --song songs/autumn_leaves.yml --out autumn --no-play
```

Add `--stems` to also write each voice (soprano/alto/tenor/bass) and drums as
its own standalone MIDI file alongside the main one — `autumn_soprano.mid`,
`autumn_bass.mid`, ... — directly importable into a DAW for external
mixing/mastering. Works for both the song path and the flat `--keys` path;
needs split stems (the default — `--no-split-stems` disables it).

## The song file

A *song* is global settings + `defaults` + an ordered list of `sections`. Each
section overrides the defaults and supplies its own `keys`:

```yaml
title: Autumn Leaves
tempo: 116
soundfont: SoundFonts/arachno.sf2

defaults:                      # applied to every section unless overridden
  instrument: epiano
  voices: { bass: 32 }         # per-voice GM program
  bass: { style: walking, step: 0.5 }
  satb: arpeggio
  chord_length: h
  perc:
    main: "er,eg,er,eg, er,eg,er,ei"
    fill_rate: 0.08

sections:
  - name: head
    repeat: 2                  # play this section twice
    keys: "A::min7, D::7, G::maj7, C::maj7"

  - name: solo
    repeat: 2
    instrument: saw            # override just for this section
    perc: { fill_rate: 0.18 }  # busier fills in the solo
    keys: "A::min7, D::7, G::maj7, C::maj7"

  - name: outro
    satb: block
    perc: { fill_rate: 0.02 }  # settle down
    keys: "A::min7, D::7, G::min, G::min"
```

## Add a melody

A section can carry a real tune on top of the harmony. Set `melody` to a line in
the [scale-degree grammar](../reference/token-grammar.md) (`q1 e2 e3 q5 …`); it
plays on the **soprano** channel and replaces the SATB soprano for that section,
so the top line is the melody rather than an arpeggio. Give it its own patch with
`voices: { soprano: … }`.

```yaml
defaults:
  key: C            # tonic for the melody (else inferred from the chords)
  mode: major       # major | minor | dorian | …
  voices: { soprano: sax }   # the lead patch

sections:
  - name: head
    melody: "q5 q6 q7 h1' q7 q6 h5"   # scale degrees; b3/#4 for accidentals
    keys: "A::min7, D::7, G::maj7, C::maj7"
```

The melody tiles to fill the section, so write one phrase and let `repeat` loop it.
Use `melody_relative: chord` to have a short motif re-fit each chord (degree 1
lands on the current chord's root) — nice for solos over changes. Sections without
a `melody` keep their SATB top voice as before. Worked example:
[`songs/kiss.yml`](https://github.com/galenspikes/music-generator/blob/main/songs/kiss.yml).
See [ADR-0005 (scale degrees)](../explanation/decisions/0005-scale-degree-melody.md)
for why the grammar uses degrees, and
[token grammar §4](../reference/token-grammar.md) for the full syntax
(accidentals, octave marks, rests).

## Add a lead (the hook)

Where `melody` plays a literal tune on the soprano channel, `lead` is a
*generator*: it states a short motif and develops it across the section —
restated and transposed to fit each chord, answered with inversions and
sequences, with call-and-response silence between phrases. The lead gets its
own 5th channel (and its own stem with `--stems`), and the full SATB keeps
playing underneath it:

```yaml
sections:
  - name: chorus
    keys: "F::maj7, G::7, E::min7, A::min7"
    lead:
      instrument: sax          # any GM name/alias/number (default: sax)
      motif: "q1 e2 e3 q5 hr"  # scale-degree grammar; omit to auto-generate
      density: 0.5             # 0-1, only used when generating: busier motif
      rests: 0.3               # 0-1: chance a response phrase stays silent
      register: high           # low | mid | high
```

- **Pitch rule (hybrid):** degrees resolve against the section `key`/`mode`
  (inferred from the chords when unset); any note landing on a strong beat
  snaps to the nearest tone of the chord sounding under it, so the line
  always agrees with the harmony. The final note cadences on a chord tone.
- **Motif:** give one in the [scale-degree grammar](../reference/token-grammar.md)
  and it is developed verbatim-first; omit it and one is generated
  (seed-reproducible via `--seed`).
- Per-section like everything else — put `lead` only on the chorus/solo, and
  target it in `mix` (`mix: { lead: {reverb: 60, vol: 110} }`) like any voice.

## DRY song structure: `blocks` + `form`

Instead of writing out every repeat of a verse/chorus by hand, define each
section once under `blocks` and sequence them by name under `form`:

```yaml
blocks:
  verse:  { keys: "A::min7, D::7, G::maj7, C::maj7", bars: 4,
            bass: { style: root } }
  chorus: { keys: "F::maj7, G::7, E::min7, A::min7", bars: 4,
            bass: { style: octaves }, voices: { soprano: saw } }

form: [verse, chorus, verse, chorus]
```

Each occurrence gets a default name from its block (`verse`, then `verse-2` on
repeat) so tempo/program events stay easy to trace. Give one occurrence its own
tweak — a louder second chorus, say — with a `{block_name: overrides}` entry
instead of a bare name:

```yaml
form: [verse, chorus, verse, {chorus: {tempo: 130, perc: {fill_rate: 0.2}}}]
```

`form` + `blocks` replaces `sections` entirely when present; use whichever
reads better for a given song (a linear chart is often clearer as plain
`sections`, a repeating song form is clearer as `blocks` + `form`).

## Transitions between sections

By default sections hard-cut into each other. A section can opt into a
`transition` to smooth the boundary:

```yaml
sections:
  - name: verse
    keys: "..."
    transition: { fill: 1bar, crash: true }
```

- `fill` replaces the last N bars of the section's drum timeline with a fill
  (drawn from the section's `perc.interrupters`, or the main pattern if none
  are set) — accepts a bar count (`1`, `1.5`) or a `"1bar"`/`"2bars"` string.
- `crash` adds a crash-cymbal hit on the *next* section's downbeat (skipped on
  the last section, since there's nothing after it to accent).

Voice leading also carries across the cut automatically: the soprano line and
bass register continue from the end of one section into the start of the
next, instead of every section re-centering its voicing from scratch.

## Dynamics arc

Give a section a `dynamics.intensity` to shape the piece's loudness/density
over time — a quiet verse building into a loud chorus, say:

```yaml
sections:
  - name: verse
    keys: "..."
    dynamics: { intensity: 0.6 }
  - name: chorus
    keys: "..."
    dynamics: { intensity: 1.1 }
```

`intensity` defaults to `1.0` (the engine's plain defaults: chord/voice
velocity base 78, percussion density as configured by `perc.fill_rate`).
Below 1.0 softens both; above 1.0 pushes both harder. It scales:
- **velocity** — chord, voice, and drum note-on velocities, at render time
  (multiplies the base before the human/random velocity humanization runs).
- **percussion density** — the section's `perc.fill_rate` (probability of a
  fill motif vs. the main pattern), scaled down for a sparser feel or up for
  a busier one.

## Targeting a length

Rather than sizing each section's `bars`/`repeat` by hand, give the song a
target duration and let it loop the whole form to fit:

```yaml
title: Long Groove
tempo: 120
length: { seconds: 1200 }   # ~20 minutes

sections:
  - name: verse
    keys: "..."
  - name: chorus
    keys: "..."
```

The full section sequence repeats (`verse`, `chorus`, `verse-loop2`,
`chorus-loop2`, ...) until the arrangement's real-world duration — computed
per section from its own tempo, since per-section tempo means beats-to-seconds
isn't constant across the song — reaches the target. The final repeat is
trimmed (its length re-expressed in `bars`) to land exactly on target rather
than overshooting by a whole extra pass. Combine with `form`/`blocks` to keep
a repeating song structure readable at any length.

## Mix / FX per section

Set volume (CC7), pan (CC10), reverb send (CC91), and chorus send (CC93) per
voice — or the whole drum kit — to push a section forward or back in the mix,
widen/narrow it, or add space, all without swapping soundfonts:

```yaml
sections:
  - name: verse
    keys: "..."
    mix: { bass: {reverb: 20} }
  - name: solo
    keys: "..."
    mix: { soprano: {vol: 110, pan: 90, reverb: 90, chorus: 40},
           bass: {vol: 100, pan: 30},
           drums: {reverb: 40} }
```

Keys under `mix` are voice names (`soprano`/`alto`/`tenor`/`bass`) or
`drums`; values are `vol`/`pan`/`reverb`/`chorus` in the standard MIDI 0–127
range (pan: 0=hard left, 64=centre, 127=hard right). Requires split stems
(the default) for the SATB voices, same as per-voice `instrument`/`voices`.
A section without `mix` sends nothing (whatever came before — the
soundfont's defaults, or the song-global `pan_spread` — carries through
unchanged).

## Groove: bass locked to the kick, and ghost notes

Two knobs make a section feel more like a real rhythm section:

```yaml
sections:
  - name: groove
    keys: "..."
    bass: { style: root, lock_kick: true }
    perc: { main: "qb,eg,qc,eg", ghost_rate: 0.15, ghost_note: c }
```

- **`bass.lock_kick`** times an independent bass line's onsets exactly to
  this section's kick-drum hits, instead of the even `bass.step`
  subdivision — the pitch pattern (`root`/`octaves`/`fifths`/`walking`/`arp`)
  is unchanged, just re-timed. Needs a `bass.style` other than `follow`/
  `none`. Falls back to the step subdivision for any chord slot with no
  kick in its span, so the bass never goes silent — this means a very short
  `chord_length` (many slots) with a sparse kick pattern will show the lock
  in fewer places than a longer `chord_length`.
- **`perc.ghost_rate`** fills empty (rest) slots in the drum pattern with a
  low-velocity ghost hit at that probability per slot — `perc.ghost_note`
  picks which drum-map letter (default `c` = snare). `0` (default) is a
  no-op.

A third knob, `perc.pocket`, lays chosen drums back behind the grid without
editing the pattern's tokens — `pocket: {c: 0.03}` delays every snare hit by
0.03 beats (~15 ms at 120 bpm). Delay-only; a hit whose token carries its own
`[to..]` modifier keeps the authored value.

All three are also available on the flat `--keys` CLI path:
`--bass-lock-kick`, `--perc-ghost-rate`, `--perc-ghost-note`,
`--perc-pocket "c:0.03"`.

## Feel presets

Instead of tuning swing/ghosts/pocket/bass-lock individually, name a *feel*
— at song level (in `defaults`) or per section:

```yaml
defaults:
  feel: laidback        # tight | laidback | swing | funk

sections:
  - name: verse
    keys: "..."
  - name: solo
    keys: "..."
    feel: funk          # this section grooves harder
```

A feel is nothing but a bundle of the raw knobs (`swing`,
`perc.ghost_rate`, `perc.pocket`, `bass.lock_kick` — see `feel.py` for the
exact values), applied *between* the engine defaults and your explicit
settings: anything you write out yourself always wins over the preset. One
caveat: swing is song-global, so a per-section `feel`'s swing amount is
ignored — put the feel in `defaults` (or set `swing` there) when you want
its swing.

## The pattern

The arrangement layer is where the *evolution* lives: keep `keys` similar across
sections but **change the texture** — instrument, `satb` style, `bass` style, and
especially `perc.fill_rate` — so the piece develops rather than just loops. Use the
existing files in `songs/` as worked templates.

## See also
[arrangement design note](../design-notes/arrangement-plan.md) ·
[Kiss On My List song study](../explanation/song-studies/kiss-on-my-list.md)
