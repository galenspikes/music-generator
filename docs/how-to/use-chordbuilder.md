# ChordBuilder quick start

*Goal: explore chord progressions by tapping — no typing, no theory needed —
then carry a progression you like into the full instrument.*

Open it: **<https://gsp87-music-generator.hf.space/chords/>**
(the main instrument links to it as **ChordBuilder** in the top bar, and the
landing page lists it too).

## What ChordBuilder is

ChordBuilder is a **focused, tap-based instrument for building and auditioning
chord progressions**. Where the [full instrument](use-the-web-instrument.md) is a
whole arrangement — harmony, voices, bass, drums — ChordBuilder does one thing
well: help you find a sequence of chords you like. There's **no text entry for
chord data anywhere** — you build everything by tapping.

It shares the same backend as the full instrument but is otherwise its own app
(it even installs as a standalone PWA).

## Build a progression

1. **Add a chord** — tap **+ chord**. You get a card you can shape by tapping:
   - **root** (C, C#, D, …),
   - **quality** (maj7, min9, sus, quartal, … — the same recipe catalog the full
     instrument uses),
   - **inversion** (which chord tone sits in the bass),
   - **play mode** for that card: *strike* (hit it), *sustain* (hold it), or
     *arpeggio* (roll through the notes).
2. **Not sure what you want?** Tap the **🎲 randomize** button for a random
   root/quality (and sometimes an inversion) — a fast way to stumble onto ideas.
3. **Repeat a section** — group chords into an `[a, b, c]*N` block so a phrase
   loops N times without re-adding it.
4. **Reorder / remove** cards until the run feels right.

## Hear it

- Tap a single card to preview **that chord** on its own.
- Use the transport to **play the whole progression** back in order.
- Pick the **instrument** (piano, e-piano, strings, …) for playback; the choice is
  remembered between visits.

## Save your progressions

**Save** stores the progression in ChordBuilder's **library** (server-side), with a
title and tags, so you can reopen it later or keep several variations side by side
("save as a new copy" gives each one its own slot). Your in-progress draft is also
kept automatically in the browser, so a refresh won't lose it.

## Take a progression into the full instrument

ChordBuilder and the full instrument speak the **same chord grammar**, so a
progression moves over as text:

1. In ChordBuilder, read the chord tokens off your cards (e.g. `C::maj7`,
   `A::min9`, `D::min7`, `G::13`; a group shows as `[A, G]*4`).
2. Open the **[full instrument](use-the-web-instrument.md)** → **Editor** tab →
   **Harmony › keys**.
3. Type (or paste) the progression there. Now you can add voicing, bass, drums,
   tempo, and export MIDI.

The two apps cross-link in their headers/footers so you can hop between them. See
the [chord grammar](write-chord-progressions.md) for the token syntax both share.

## ChordBuilder vs. the full instrument — which do I use?

- **ChordBuilder** — when you want to *find chords*: quick, tactile, no
  distractions. Great on a phone.
- **Full instrument** — when you want to *build a piece*: turn a progression into a
  full arrangement with voices, bass, percussion, and a MIDI export.

Start in ChordBuilder, finish in the full instrument.

## See also
[Use the web instrument](use-the-web-instrument.md) ·
[Write chord progressions](write-chord-progressions.md) ·
[token grammar](../reference/token-grammar.md)
