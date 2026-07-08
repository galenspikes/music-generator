# How to render audio

*Goal: turn a generation into a normalized WAV. The generator writes MIDI;
`render.py` (or the `./play_music` shim) adds the FluidSynth → ffmpeg audio stage.*

## Prerequisites

```bash
brew install fluidsynth ffmpeg     # audio toolchain
```

You also need a SoundFont (`.sf2`). `SoundFonts/` is gitignored — supply your own.

## Render and keep a WAV

`render.py` consumes its own wrapper flags and forwards the rest to the generator:

```bash
./play_music --save-wav --sf2 SoundFonts/arachno.sf2 \
  --keys "C::maj9, A::min11" --seconds 60 --out my_take
```

`./play_music` is a thin shim over `render.py`; the two are interchangeable.

## Useful wrapper flags

| Flag | Effect |
|---|---|
| `--save-wav` | render and keep a WAV (otherwise MIDI only) |
| `--sf2 PATH` | SoundFont (also forwarded to the generator) |
| `--fx {chorus-super,lush,dry,none}` | FX preset (or `--chorus-super`) |
| `--normalize` | ffmpeg loudnorm to −14 LUFS |
| `--boost-db N` / `--boost-normalize N` | volume boost (after normalize) |
| `--no-play` | skip playback |
| `--output-dir DIR` | WAV output directory |
| `--stems` | also bounce each voice + drums to its own WAV (needs `--save-wav`) |

## Where output lands

Everything goes under `output/{midi,audio,metadata}/<slug>/`. The `output/` tree is
gitignored.

## Tips
- For a polished master: `--normalize` (consistent loudness) then a small
  `--boost-db` if needed.

## Stems for external mixing

The engine splits stems by default (`--split-stems`), putting each voice on
its own MIDI channel. Add `--stems` to also bounce each one to its own WAV,
directly importable into a DAW:

```bash
./play_music --save-wav --stems --sf2 SoundFonts/arachno.sf2 \
  --keys "C::maj9, A::min11" --seconds 60 --out my_take
```

This writes `my_take.wav` (the full mix) plus `my_take_soprano.wav`,
`my_take_alto.wav`, `my_take_tenor.wav`, `my_take_bass.wav`, and
`my_take_drums.wav` alongside it. Stems are raw FluidSynth renders —
`--normalize`/`--boost-db` only apply to the main mix, since independently
loudness-matching each stem would destroy the relative balance between them
(the whole point of exporting stems). Works with `--song` arrangements too.

## See also
[CLI reference](../reference/cli-reference.md) · [architecture — render pipeline](../explanation/architecture.md)
