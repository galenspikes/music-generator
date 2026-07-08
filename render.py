#!/usr/bin/env python3
# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""Render wrapper: generate MIDI, then (optionally) render/normalize/boost audio.

Python port of the old `play_music` zsh wrapper. Pipeline:
  music_generator.py  ->  FluidSynth (WAV)  ->  ffmpeg (loudnorm / boost)  ->  play

Wrapper flags (consumed here); everything else is forwarded to the generator:
  --sf2 PATH            SoundFont (also forwarded to the generator)
  --fx NAME             FX preset: chorus-super | lush | dry | none
  --chorus-super        alias for --fx chorus-super
  --normalize           ffmpeg loudnorm (to -14 LUFS, 44.1 kHz)
  --boost-db N          ffmpeg volume boost (dB)
  --boost-normalize N   normalize, then boost by N dB
  --save-wav            render+keep a WAV (otherwise MIDI only)
  --stems               also bounce each voice + drums stem MIDI to its own
                        raw WAV (forwards --stems to the generator)
  --no-play             skip playback
  --output-dir DIR      WAV output dir (default from config.json, else 'audio')
  --keep-temporary      keep intermediate WAVs
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
GENERATOR = SCRIPT_DIR / "music_generator.py"
CONFIG_PATH = SCRIPT_DIR / "config.json"
SOUNDFONTS_DIR = SCRIPT_DIR / "SoundFonts"

# Matches MidiOut.write_stems's naming: <base>_<name>.mid alongside the main
# MIDI ("lead" only exists when the song used one; find_stem_midis skips
# whichever stems weren't written).
STEM_NAMES = ("soprano", "alto", "tenor", "bass", "lead", "drums")

FX_PRESETS: dict[str, list[str]] = {
    "none": [],
    "dry": ["-o", "synth.chorus.active=0", "-o", "synth.reverb.active=0"],
    "chorus-super": [
        "-o", "synth.chorus.active=1", "-o", "synth.chorus.nr=5",
        "-o", "synth.chorus.level=8", "-o", "synth.chorus.depth=8",
        "-o", "synth.chorus.speed=0.30",
    ],
    "lush": [
        "-o", "synth.chorus.active=1", "-o", "synth.chorus.level=7",
        "-o", "synth.chorus.depth=10", "-o", "synth.chorus.speed=0.40",
        "-o", "synth.reverb.active=1", "-o", "synth.reverb.level=0.8",
        "-o", "synth.reverb.room-size=0.7",
    ],
}


def find_tool(name: str) -> str | None:
    """Locate a CLI tool by absolute path then PATH (so it works even when the
    caller's PATH is minimal — the bug that bit the old shell wrapper)."""
    for cand in (f"/opt/homebrew/bin/{name}", f"/usr/local/bin/{name}"):
        if Path(cand).is_file():
            return cand
    return shutil.which(name)


def list_soundfonts(soundfonts_dir: Path = SOUNDFONTS_DIR) -> list[str]:
    """Available .sf2 filenames in the soundfonts directory (unsorted glob,
    sorted for stable output). SoundFonts/ is user-supplied and gitignored —
    there's nothing bundled to discover in a fresh checkout."""
    if not soundfonts_dir.is_dir():
        return []
    return sorted(p.name for p in soundfonts_dir.glob("*.sf2"))


def resolve_sf2(value: str | None, soundfonts_dir: Path = SOUNDFONTS_DIR) -> str | None:
    """Resolve --sf2 for convenience: a real path (or one containing a path
    separator) is used as-is; a bare name resolves against the soundfonts
    directory, trying the name as given and with a .sf2 suffix. Falls back to
    the original value unchanged if nothing matches, so existing full-path
    usage and error handling are unaffected."""
    if not value or Path(value).is_file() or "/" in value or "\\" in value:
        return value
    for candidate in (soundfonts_dir / value, soundfonts_dir / f"{value}.sf2"):
        if candidate.is_file():
            return str(candidate)
    return value


def load_config(path: Path = CONFIG_PATH) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _config_output_dir(cfg: dict) -> str | None:
    for entry in cfg.get("default_wrapper_flags") or []:
        flat = entry if isinstance(entry, (list, tuple)) else [entry]
        flat = [str(x) for x in flat]
        if "--output-dir" in flat:
            i = flat.index("--output-dir")
            if i + 1 < len(flat):
                return flat[i + 1]
    return None


def fx_opts(preset: str, have_sf2: bool) -> list[str]:
    if not have_sf2:
        return []
    if preset not in FX_PRESETS:
        raise SystemExit(
            f"Unknown FX preset '{preset}'. Choices: {', '.join(FX_PRESETS)}")
    return list(FX_PRESETS[preset])


# ---- command builders (pure -> testable) ----

def fluidsynth_render_cmd(fs: str, opts: list[str], wav: str, sf2: str,
                          mid: str) -> list[str]:
    return [fs, "-q", "-ni", *opts, "-F", wav, sf2, mid]


def ffmpeg_loudnorm_cmd(ff: str, src: str, dst: str) -> list[str]:
    return [ff, "-y", "-hide_banner", "-loglevel", "error", "-i", src,
            "-af", "loudnorm=I=-14:TP=-1.0:LRA=11", "-ar", "44100", dst]


def ffmpeg_volume_cmd(ff: str, src: str, dst: str, db: str) -> list[str]:
    return [ff, "-y", "-hide_banner", "-loglevel", "error", "-i", src,
            "-af", f"volume={db}dB", dst]


def run_generator(gen_args: list[str]) -> str:
    """Run the MIDI generator; return the path it printed ('Wrote <path>')."""
    proc = subprocess.run([sys.executable, str(GENERATOR), *gen_args],
                          capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    for line in proc.stdout.splitlines():
        if line.startswith("Wrote "):
            return line[len("Wrote "):].strip()
    raise SystemExit("❌ No MIDI produced (generator failed?).")


def find_stem_midis(midi_path: str) -> dict[str, str]:
    """Sibling stem MIDI files `MidiOut.write_stems` wrote next to `midi_path`
    (e.g. `song.mid` -> `song_soprano.mid`, ..., `song_drums.mid`). Returns
    `{name: path}` for whichever stems exist (empty if `--stems` wasn't
    passed to the generator, or split stems were off)."""
    p = Path(midi_path)
    base = p.stem
    found = {}
    for name in STEM_NAMES:
        candidate = p.parent / f"{base}_{name}{p.suffix}"
        if candidate.is_file():
            found[name] = str(candidate)
    return found


def post_process(ff: str, wav: str, *, normalize: bool, boost_db: str | None,
                 boost_after_norm: str | None,
                 keep_temporary: bool) -> tuple[str, list[str]]:
    """Run the ffmpeg normalize/boost chain; return (final_wav, intermediates)."""
    current = wav
    prev: list[str] = []
    if normalize or boost_after_norm:
        norm = current[:-4] + "_norm.wav"
        print("Normalizing audio")
        subprocess.run(ffmpeg_loudnorm_cmd(ff, current, norm), check=True)
        prev.append(current)
        current = norm
    if boost_db:
        boosted = f"{current[:-4]}_+{boost_db}dB.wav"
        print(f"Boosting audio by {boost_db} dB")
        subprocess.run(ffmpeg_volume_cmd(ff, current, boosted, boost_db),
                       check=True)
        prev.append(current)
        current = boosted
    if boost_after_norm:
        combo = f"{current[:-4]}_+{boost_after_norm}dB.wav"
        print(f"Boosting post-normalize by {boost_after_norm} dB")
        subprocess.run(ffmpeg_volume_cmd(ff, current, combo, boost_after_norm),
                       check=True)
        prev.append(current)
        current = combo
    if not keep_temporary:
        for old in prev:
            if old != current and Path(old).is_file():
                Path(old).unlink()
    return current, prev


def build_parser(default_sf2: str | None, default_output_dir: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generate MIDI and optionally render/normalize audio.",
        allow_abbrev=False)  # don't let --chorus match --chorus-super
    p.add_argument("--sf2", default=default_sf2,
                   help="SoundFont path, or a bare name resolved against "
                   "SoundFonts/ (e.g. --sf2 arachno for SoundFonts/arachno.sf2).")
    p.add_argument("--list-soundfonts", action="store_true",
                   help=f"List .sf2 files found in {SOUNDFONTS_DIR}/ and exit.")
    p.add_argument("--fx", default="dry")
    p.add_argument("--chorus-super", dest="fx", action="store_const",
                   const="chorus-super")
    p.add_argument("--normalize", action="store_true")
    p.add_argument("--boost-db", default=None)
    p.add_argument("--boost-normalize", dest="boost_after_norm", default=None)
    p.add_argument("--no-play", dest="no_play", action="store_true")
    p.add_argument("--save-wav", dest="save_wav", action="store_true")
    p.add_argument("--output-dir", dest="output_dir", default=default_output_dir)
    p.add_argument("--keep-temporary", dest="keep_temporary", action="store_true")
    p.add_argument(
        "--stems", action="store_true",
        help="Also bounce each voice + drums stem MIDI (forwards --stems to "
        "the generator) to its own raw WAV alongside the main one, for "
        "external mixing. Stems are not independently normalized/boosted — "
        "that would destroy the relative balance between them. Needs "
        "--sf2 and --save-wav.")
    return p


def main(argv: list[str] | None = None) -> int:
    cfg = load_config()
    parser = build_parser(cfg.get("default_sf2"),
                          _config_output_dir(cfg) or "audio")
    args, forwarded = parser.parse_known_args(argv)

    if args.list_soundfonts:
        names = list_soundfonts(SOUNDFONTS_DIR)
        if not names:
            print(f"No .sf2 files found in {SOUNDFONTS_DIR}/ "
                  "(SoundFonts/ is gitignored — supply your own).")
        else:
            print(f"Available soundfonts in {SOUNDFONTS_DIR}/:")
            for name in names:
                print(f"  {name}")
        return 0

    args.sf2 = resolve_sf2(args.sf2, SOUNDFONTS_DIR)

    # Generator args: forwarded unknowns + config defaults + (--sf2 is dual-use)
    gen_args = list(forwarded) + [str(x) for x in
                                  (cfg.get("default_generator_flags") or [])]
    if args.sf2:
        gen_args += ["--sf2", args.sf2]
    if args.stems:
        gen_args += ["--stems"]

    fluidsynth = find_tool("fluidsynth")
    ffmpeg = find_tool("ffmpeg")
    needs_ffmpeg = args.normalize or args.boost_db or args.boost_after_norm
    if args.sf2 and not fluidsynth:
        raise SystemExit("❌ --sf2 provided but fluidsynth is not available.")
    if needs_ffmpeg and not ffmpeg:
        raise SystemExit("❌ ffmpeg is required for normalize/boost options.")

    opts = fx_opts(args.fx, bool(args.sf2))

    midi = run_generator(gen_args)
    slug = Path(midi).parent.name
    base = Path(midi).stem
    audio_dir = Path(args.output_dir) / slug
    meta_dir = SCRIPT_DIR / "output" / "metadata" / slug   # unified under output/
    audio_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    final_wav = None
    stem_wavs: dict[str, str] = {}
    if args.save_wav:
        if not args.sf2:
            print("ℹ️ --save-wav needs --sf2; skipping WAV render.")
        else:
            if opts:
                print(f"✨ FX preset '{args.fx}'")
            wav = str(audio_dir / f"{base}.wav")
            print(f"Rendering WAV -> {wav}")
            subprocess.run(fluidsynth_render_cmd(fluidsynth, opts, wav,
                                                 args.sf2, midi), check=True)
            final_wav, _ = post_process(
                ffmpeg, wav, normalize=args.normalize, boost_db=args.boost_db,
                boost_after_norm=args.boost_after_norm,
                keep_temporary=args.keep_temporary)

            if args.stems:
                # Raw FluidSynth render, no normalize/boost: independently
                # loudness-matching each stem would destroy the relative
                # balance between them, which is the whole point of stems.
                for name, stem_mid in find_stem_midis(midi).items():
                    stem_wav = str(audio_dir / f"{base}_{name}.wav")
                    print(f"Rendering stem WAV -> {stem_wav}")
                    subprocess.run(
                        fluidsynth_render_cmd(fluidsynth, opts, stem_wav,
                                              args.sf2, stem_mid),
                        check=True)
                    stem_wavs[name] = stem_wav
    else:
        print("ℹ️ Skipping WAV render (use --save-wav to enable).")

    meta_path = meta_dir / f"{base}.json"
    meta_path.write_text(json.dumps({
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator_args": gen_args,
        "outputs": {"final_wav": final_wav, "latest_midi": midi,
                    "wav_saved": bool(final_wav), "stem_wavs": stem_wavs},
        "render": {"soundfont": args.sf2 or None, "fx_preset": args.fx,
                   "output_dir": args.output_dir},
        "post_processing": {"normalize": bool(args.normalize),
                            "boost_db": args.boost_db,
                            "boost_after_normalize_db": args.boost_after_norm},
    }, indent=2), encoding="utf-8")
    print(f"🧾 Metadata → {meta_path}")

    if not args.no_play:
        afplay = shutil.which("afplay")
        if final_wav and afplay:
            print(f"▶️  Playing {final_wav}")
            subprocess.run([afplay, final_wav])
        elif args.sf2 and fluidsynth:
            print("▶️  Playing via FluidSynth")
            subprocess.run([fluidsynth, "-q", "-i", *opts, args.sf2, midi])
        else:
            print("ℹ️  No playback backend available; skipping.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
