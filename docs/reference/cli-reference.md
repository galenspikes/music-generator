# CLI reference

*Reference — the command-line flags for the generator and the audio render
wrapper. Captured from `--help`; regenerate when flags change.*

Duration codes used by `--chord-length` and throughout the token DSL:
`w`=whole, `h`=half, `q`=quarter, `e`=eighth, `s`=sixteenth, `t`=thirty-second.
See [reference/token-grammar.md](token-grammar.md) for the full grammar.

## `music_generator.py` — generate MIDI

```text
usage: music_generator.py [-h] [--song SONG] [--keys KEYS] [--random-roots]
                          [--full-progression] [--keys-preset KEYS_PRESET]
                          [--chords {chromatic-mediants,extended-chords,triads,sevenths,ninths,quartal,sus,add6,lyd-dom} [{chromatic-mediants,extended-chords,triads,sevenths,ninths,quartal,sus,add6,lyd-dom} ...]]
                          [--chords-order {random,roundrobin}]
                          [--instrument INSTRUMENT]
                          [--voice-instrument VOICE=NAME]
                          [--bass-style {follow,none,root,octaves,fifths,walking,arp}]
                          [--bass-step BASS_STEP] [--bass-lock-kick]
                          [--bpm BPM] [--chord-length {w,h,q,e,s,t}]
                          [--chord-interrupters [CHORD_INTERRUPTERS ...]]
                          [--satb-style {block,static,counterpoint,arpeggio}]
                          [--voicing {satb,dense}]
                          [--counterpoint-step COUNTERPOINT_STEP]
                          [--counterpoint-suspension-prob COUNTERPOINT_SUSPENSION_PROB]
                          [--counterpoint-anticipation-prob COUNTERPOINT_ANTICIPATION_PROB]
                          [--perc-main PERC_MAIN] [--no-perc]
                          [--perc-interrupters [PERC_INTERRUPTERS ...]]
                          [--perc-lib PERC_LIB]
                          [--perc-main-key PERC_MAIN_KEY]
                          [--perc-interrupter-keys [PERC_INTR_KEYS ...]]
                          [--perc-stages [PERC_STAGES ...]]
                          [--perc-fill-curve PERC_FILL_CURVE]
                          [--perc-ghost-rate PERC_GHOST_RATE]
                          [--perc-ghost-note PERC_GHOST_NOTE]
                          [--perc-fill-rate PERC_FILL_RATE]
                          [--velocity-mode-chords {uniform,random,human}]
                          [--velocity-mode-drums {uniform,random,human}]
                          [--chord-fill-rate CHORD_FILL_RATE]
                          [--seconds SECONDS] [--out OUT] [--seed SEED]
                          [--sf2 SF2] [--no-play] [--split-stems]
                          [--no-split-stems] [--swing SWING]
                          [--pan-spread PAN_SPREAD] [--stems]

Harmony + Percussion generator (independent parts, SATB, interrupters).

options:
  -h, --help            show this help message and exit
  --song SONG           Path to a YAML song file (arrangement of sections).
                        When set, section-based rendering is used and most
                        other flags are ignored.
  --keys KEYS           Comma list of keys/chords (e.g.
                        'C::maj7,F::maj7,G::13'). Honored by default and
                        cycled to fill the piece. Ignored if --random-roots is
                        set.
  --random-roots        Shuffle a circle-of-fifths for the chord roots each
                        run, ignoring --keys. Loops to fill the piece.
  --full-progression    Play the roots through once with no looping/repeats,
                        instead of cycling — either your --keys chart or,
                        without --keys, a full circle-of-fifths walk.
  --keys-preset KEYS_PRESET
                        Name of preset from library/keys_presets.json
  --chords {chromatic-mediants,extended-chords,triads,sevenths,ninths,quartal,sus,add6,lyd-dom} [{chromatic-mediants,extended-chords,triads,sevenths,ninths,quartal,sus,add6,lyd-dom} ...]
                        Chord families to use.
  --chords-order {random,roundrobin}
                        How to pick among multiple chord families each step.
  --instrument INSTRUMENT
                        GM program: name alias (e.g., 'strings', 'flute') or
                        0–127
  --voice-instrument VOICE=NAME
                        Per-voice instrument override, e.g. --voice-instrument
                        bass=bass (repeatable). Voices: soprano, alto, tenor,
                        bass. Voices not set use --instrument. Requires split
                        stems (the default).
  --bass-style {follow,none,root,octaves,fifths,walking,arp}
                        Bass line generator: 'follow' (bass tracks the SATB
                        voicing), 'none' (no bass voice at all), or an
                        independent line: root, octaves, fifths, walking, arp.
                        Requires split stems.
  --bass-step BASS_STEP
                        Subdivision (in beats) for the bass line when --bass-
                        style is not 'follow' (0.5 = eighths, 1.0 = quarters).
  --bass-lock-kick      Lock the independent bass line's timing to the drum
                        pattern's kick hits instead of the even --bass-step
                        subdivision (pitch pattern is unchanged). Requires
                        --bass-style other than 'follow'/'none'.
  --bpm BPM
  --chord-length {w,h,q,e,s,t}
  --chord-interrupters [CHORD_INTERRUPTERS ...]
                        Motifs like "ec,er,sc" (multiple allowed)
  --satb-style {block,static,counterpoint,arpeggio}
                        Voicing style for SATB harmony: block chords (re-
                        voices each hit), static (freezes the voicing across
                        an unchanged chord — no wobble), or
                        counterpoint/arpeggio lines.
  --voicing {satb,dense}
                        satb = 4-voice voicing (default). dense = sound EVERY
                        chord tone spread across the register (full
                        11ths/13ths, quartal, clusters, mystic/messiaen) on
                        one timbre — for rich, colorful harmony.
  --counterpoint-step COUNTERPOINT_STEP
                        Subdivision length in beats when using counterpoint
                        SATB style.
  --counterpoint-suspension-prob COUNTERPOINT_SUSPENSION_PROB
                        Probability per voice that a chord change introduces a
                        suspension (0–1).
  --counterpoint-anticipation-prob COUNTERPOINT_ANTICIPATION_PROB
                        Probability per voice that a chord change introduces
                        an anticipation (0–1).
  --perc-main PERC_MAIN
                        Pattern like "qk,eh,esh,er". Pass "" for silence.
  --no-perc             Silence percussion entirely (same as --perc-main '').
  --perc-interrupters [PERC_INTERRUPTERS ...]
                        Motifs like "sh,sh,skh,sh" ...
  --perc-lib PERC_LIB
  --perc-main-key PERC_MAIN_KEY
  --perc-interrupter-keys [PERC_INTR_KEYS ...]
  --perc-stages [PERC_STAGES ...]
                        Sequential percussion stages like
                        '16:sh,sh,skh,sh|qk,er,qs,er' or '@grooveA'.
  --perc-fill-curve PERC_FILL_CURVE
                        Linear fill-rate ramp 'start:end' (0-1) applied across
                        perc stages.
  --perc-ghost-rate PERC_GHOST_RATE
                        0-1. Probability of filling an empty drum slot with a
                        low-velocity ghost note (default: snare). Default=0.0
                        (off).
  --perc-ghost-note PERC_GHOST_NOTE
                        Drum-map letter for the ghost note (default 'c' =
                        snare).
  --perc-fill-rate PERC_FILL_RATE
                        0–1. Probability a *percussion* interrupter replaces
                        the main pattern. Default=0.20.
  --velocity-mode-chords {uniform,random,human}
                        Chord velocity behaviour: uniform, random, or
                        humanised
  --velocity-mode-drums {uniform,random,human}
                        Drum velocity behaviour: uniform, random, or humanised
  --chord-fill-rate CHORD_FILL_RATE
                        0–1. Probability a *chord* interrupter replaces the
                        straight chord slice. Default=0.00.
  --seconds SECONDS
  --out OUT
  --seed SEED
  --sf2 SF2             Path to SoundFont (.sf2)
  --no-play             Generate MIDI only; do not launch FluidSynth.
  --split-stems         Write SATB voices to separate MIDI tracks/channels
                        (default).
  --no-split-stems      Merge SATB voices into a single MIDI track.
  --swing SWING         0–0.75. Off-beat swing: delays the 'and' of each beat
                        (0=straight eighths, 0.5=triplet swing). Default=0.0.
  --pan-spread PAN_SPREAD
                        0–1. Stereo width of the SATB voices across the field
                        (0=centred/mono, 1=widest). Needs split stems.
                        Default=0.0.
  --stems               Also write each voice + drums as its own standalone
                        MIDI file alongside the main output, for mixing
                        externally. Needs split stems (the default).
```

## `render.py` — generate + render audio

Wrapper over the generator: runs FluidSynth then ffmpeg. Wrapper flags are
consumed here; everything else is forwarded to `music_generator.py`.

```text
usage: render.py [-h] [--sf2 SF2] [--list-soundfonts] [--fx FX]
                 [--chorus-super] [--normalize] [--boost-db BOOST_DB]
                 [--boost-normalize BOOST_AFTER_NORM] [--no-play] [--save-wav]
                 [--output-dir OUTPUT_DIR] [--keep-temporary] [--stems]

Generate MIDI and optionally render/normalize audio.

options:
  -h, --help            show this help message and exit
  --sf2 SF2             SoundFont path, or a bare name resolved against
                        SoundFonts/ (e.g. --sf2 arachno for
                        SoundFonts/arachno.sf2).
  --list-soundfonts     List .sf2 files found in SoundFonts/ and exit.
  --fx FX
  --chorus-super
  --normalize
  --boost-db BOOST_DB
  --boost-normalize BOOST_AFTER_NORM
  --no-play
  --save-wav
  --output-dir OUTPUT_DIR
  --keep-temporary
  --stems               Also bounce each voice + drums stem MIDI (forwards
                        --stems to the generator) to its own raw WAV alongside
                        the main one, for external mixing. Stems are not
                        independently normalized/boosted — that would destroy
                        the relative balance between them. Needs --sf2 and
                        --save-wav.
```
