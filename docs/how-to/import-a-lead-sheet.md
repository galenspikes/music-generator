# How to import a lead sheet

*Goal: turn a lead-sheet PDF (chords + form, no melody) into a `song.yml` you can
render and edit. Chords/form only — see
[the design note](../design-notes/leadsheet-import-plan.md) for why melody/OMR is
out of scope for v1.*

This is a **workflow**, not a CLI command: Claude Code reads the PDF directly (its
Read tool handles PDFs natively — born-digital or scanned), fills in a small
intermediate chart, and calls `leadsheet.ir_to_song_yml` to emit the file. The
deterministic parts — chord-symbol mapping and YAML emission — are real, tested
code (`leadsheet.py`); reading the page is the one step that's necessarily a model,
not a parser, since chord charts come as messy scans as often as clean text.

## The steps

1. **Point Claude Code at the PDF.** Ask it to read the chart and describe what it
   sees: title, key, tempo (if printed), the sections (often labeled A/B, or
   verse/chorus, sometimes with repeat marks), and the chords measure-by-measure
   within each section.

2. **Have it fill in the IR** (the normalized chart) as a plain Python dict:

   ```python
   ir = {
       "title": "Autumn Leaves",
       "tempo": 116,
       "sections": [
           {"name": "A", "repeat": 2,
            "measures": [["Cm7", "F7"], ["Bbmaj7", "Ebmaj7"],
                        ["Adim7", "D7"], ["Gm7", "Gm7"]]},
           {"name": "B",
            "measures": [["Cm7"], ["F7"], ["Bbmaj7"], ["Ebmaj7"]]},
       ],
   }
   ```

   `measures` is a list of measures, each a list of the chord symbols that fall in
   that bar, in conventional lead-sheet notation (`Cmaj7`, `F#m7b5`, `Bb7/D`,
   `CΔ`, `Cø`, `C-7` — see `leadsheet.chordsym_to_token` for the full vocabulary
   it recognizes). **Every measure in a section must have the same number of
   chords** — 1, 2, or 4 per measure map to whole/half/quarter-note chord
   lengths. A section with a mixed density (some bars with one chord, others
   with two) needs to be split into two sections; the emitter refuses to guess
   which duration you meant.

3. **Emit the song.yml:**

   ```python
   import leadsheet as ls
   print(ls.ir_to_song_yml(ir))
   ```

   Write the result to a file, e.g. `songs/autumn_leaves_imported.yml`.

4. **Transpose if needed.** A lead sheet for a Bb instrument, or a chart with a
   capo, needs a semitone shift: `ir_to_song_yml(ir, transpose=-2)`. This shifts
   every chord root *and* slash bass together.

5. **Review, don't trust blindly.** Read the emitted YAML back against the chart —
   this is the non-negotiable verification step (see the design note). Render it:

   ```bash
   venv/bin/python music_generator.py --song songs/autumn_leaves_imported.yml --out autumn --no-play
   ```

   and listen. Vision extraction can misread a smudged chord or miscount a
   repeat; a wrong chord is easy to spot by ear once it's playing.

## What the mapper actually recognizes

`chordsym_to_token` covers the common vocabulary — triads, sevenths, extensions
(9/11/13), alterations (`b9`, `#11`, `alt`), sixths, sus chords, and slash/pedal
basses — plus the usual shorthand (`Δ` for `maj7`, `ø` for `m7b5`, `°` for `dim`,
`+` for `aug`). It is **case-sensitive where case carries meaning**: `CM7` is a
major seventh, `Cm7` is a minor seventh — don't let anything normalize that away.

An unrecognized quality raises an error rather than guessing — if a symbol from
the chart doesn't map, that's a sign either the chart used an unusual spelling
(fix the symbol) or the mapper genuinely doesn't cover it yet (extend
`leadsheet._QUALITY_ANY_CASE`, with a test).

## After import

The emitted file is a normal song — everything in
[create an arrangement](create-an-arrangement.md) applies: add a melody, tune
`perc.fill_rate` per section, override instruments. The import just gets the
chords and form down; the arrangement is yours to shape from there.

## See also
[Lead-sheet import design note](../design-notes/leadsheet-import-plan.md) ·
[Create an arrangement](create-an-arrangement.md) ·
[Token grammar reference](../reference/token-grammar.md)
