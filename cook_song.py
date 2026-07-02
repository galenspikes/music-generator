#!/usr/bin/env python3
# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""The demo library CLI — one catalog for songs and capability presets.

Two kinds of demo live here:

* **Songs** — multi-section arrangements in ``songs/*.yml`` (played via
  ``music_generator.py --song``). These are the "press demo" tunes.
* **Presets** — capability recipes in ``library/song_cookbook.py`` (a set of
  ``music_generator.py`` args). These show off the things a song file can't:
  fugue, process music, dense voicing, melody transforms, evolving percussion.

Usage:

    python cook_song.py list                # every demo, songs + presets
    python cook_song.py show kiss           # details for one demo
    python cook_song.py make kiss           # render + play via play_music
    python cook_song.py make fugue -- --sf2 SoundFonts/arachno.sf2
    python cook_song.py gallery             # render the highlight set to MIDI
"""

from __future__ import annotations

import argparse
import glob
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

from logging_config import setup_logger, log_performance, log_error


def run_command_safe(cmd: list[str], cwd: str | None = None) -> tuple[bool, int]:
    """Run a subprocess, streaming its output. Returns (success, returncode)."""
    try:
        result = subprocess.run(cmd, cwd=cwd, check=False)
        return result.returncode == 0, result.returncode
    except OSError as exc:
        cook_song_logger.error("failed to launch %s: %s", cmd[0] if cmd else "?", exc)
        return False, -1


# Setup logging
cook_song_logger = setup_logger("cook_song")


SCRIPT_DIR = Path(__file__).resolve().parent
PLAY_MUSIC = SCRIPT_DIR / "play_music"
GENERATOR = SCRIPT_DIR / "music_generator.py"
COOKBOOK_PATH = SCRIPT_DIR / "library" / "song_cookbook.py"
SONGS_DIR = SCRIPT_DIR / "songs"
MIDI_DIR = SCRIPT_DIR / "output" / "midi"
GALLERY_DIR = SCRIPT_DIR / "site" / "assets" / "midi"

if not COOKBOOK_PATH.exists():
    sys.stderr.write(f"❌ song_cookbook.py not found at {COOKBOOK_PATH}\n")
    sys.exit(1)


def _load_cookbook():
    spec = importlib.util.spec_from_file_location("song_cookbook", COOKBOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[call-arg]
    return module


COOKBOOK_MODULE = _load_cookbook()
COOKBOOK = COOKBOOK_MODULE.SONG_COOKBOOK

# The flagship — what `make demo` plays.
FLAGSHIP = "kiss"

# The curated highlight set rendered to committable MIDI by `gallery`. Each is
# (kind, name) where kind is "song" or "preset"; the output file is <name>.mid.
GALLERY: list[tuple[str, str]] = [
    ("song", "kiss"),
    ("song", "isnt_she_lovely"),
    ("song", "autumn_leaves"),
    ("song", "whiter_shade_of_pale"),
    ("preset", "dense_colors"),
    ("preset", "counterpoint"),
    ("preset", "fugue"),
    ("preset", "perc_evolution"),
]


# --------------------------------------------------------------------------- #
# Songs (YAML arrangements)
# --------------------------------------------------------------------------- #
def song_path(name: str) -> Path | None:
    """Resolve a song by stem (e.g. 'kiss' -> songs/kiss.yml). None if absent."""
    p = SONGS_DIR / f"{name}.yml"
    return p if p.exists() else None


def list_song_files() -> list[Path]:
    return sorted(SONGS_DIR.glob("*.yml"))


def song_meta(path: Path) -> tuple[str, str]:
    """Return (title, description) read from a song's YAML front-matter."""
    import yaml
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 — a malformed file shouldn't break listing
        return path.stem, ""
    return str(raw.get("title", path.stem)), str(raw.get("description", "")).strip()


# --------------------------------------------------------------------------- #
# Listing / showing
# --------------------------------------------------------------------------- #
def list_all(verbose: bool) -> None:
    songs = list_song_files()
    recipes = sorted(COOKBOOK)
    width = max([len(p.stem) for p in songs] + [len(k) for k in recipes] + [1])

    print("Songs (arrangements — the 'press demo' tunes):")
    for path in songs:
        title, desc = song_meta(path)
        line = f"  {path.stem.ljust(width)}  {title}"
        if verbose and desc:
            line += f"\n      {desc}"
        print(line)

    print("\nPresets (capability showcases):")
    for key in recipes:
        payload = COOKBOOK[key]
        title = payload.get("title", key.replace("_", " ").title())
        line = f"  {key.ljust(width)}  {title}"
        if verbose:
            desc = str(payload.get("description", "")).strip()
            if desc:
                line += f"\n      {desc}"
        print(line)

    print("\nRender one with: python cook_song.py make <name>")
    print(f"Render the flagship with: python cook_song.py make {FLAGSHIP}")


def show(name: str) -> int:
    sp = song_path(name)
    if sp is not None:
        title, desc = song_meta(sp)
        print(f"Song: {title} ({name})")
        print(f"File: {sp.relative_to(SCRIPT_DIR)}")
        if desc:
            print(f"\n{desc}\n")
        print("Render:")
        print(f"  python cook_song.py make {name}")
        print(f"  {GENERATOR.name} --song {sp.relative_to(SCRIPT_DIR)} --out {name} --no-play")
        return 0

    try:
        slug, payload = COOKBOOK_MODULE.resolve_recipe(name)
    except KeyError as exc:
        sys.stderr.write(f"❌ {exc}\n")
        return 1
    title = payload.get("title", slug.replace("_", " ").title())
    print(f"Preset: {title} ({slug})")
    aliases = payload.get("aliases", [])
    tags = payload.get("tags", [])
    if aliases:
        print(f"Aliases: {', '.join(aliases)}")
    if tags:
        print(f"Tags: {', '.join(tags)}")
    desc = str(payload.get("description", "")).strip()
    if desc:
        print(f"\n{desc}\n")
    print("play_music args:")
    print("  " + COOKBOOK_MODULE.format_command(payload.get("args", [])))
    return 0


# --------------------------------------------------------------------------- #
# Making (render + play via play_music)
# --------------------------------------------------------------------------- #
def _has_out(seq: list[str]) -> bool:
    return any(tok == "--out" or tok.startswith("--out=") for tok in seq)


def make(name: str, forward: list[str], dry_run: bool) -> int:
    if not PLAY_MUSIC.exists():
        sys.stderr.write(f"❌ play_music script not found at {PLAY_MUSIC}\n")
        return 1

    extra = forward[:]
    # `--dry-run` after the name is swallowed by REMAINDER into `forward`;
    # honour it there so `make kiss --dry-run` works as expected.
    if "--dry-run" in extra:
        dry_run = True
        extra = [e for e in extra if e != "--dry-run"]
    if extra and extra[0] == "--":
        extra = extra[1:]

    sp = song_path(name)
    if sp is not None:
        base: list[str] = ["--song", str(sp)]
        slug = name
        label = song_meta(sp)[0]
    else:
        try:
            slug, payload = COOKBOOK_MODULE.resolve_recipe(name)
        except KeyError as exc:
            sys.stderr.write(f"❌ {exc}\n")
            return 1
        base = [str(a) for a in payload.get("args", [])]
        label = payload.get("title", slug)

    if not _has_out(base) and not _has_out(extra):
        base = base + ["--out", slug]

    cmd = [str(PLAY_MUSIC)] + base + extra
    pretty = COOKBOOK_MODULE.format_command(cmd)
    if dry_run:
        print(pretty)
        return 0
    print(f"🍳 Cooking '{label}'...")
    print(f"➡️  {pretty}")
    success, _ = run_command_safe(cmd, cwd=str(SCRIPT_DIR))
    if not success:
        print("❌ play_music failed")
        return 1
    return 0


# --------------------------------------------------------------------------- #
# Gallery (batch render the highlight set to committable MIDI)
# --------------------------------------------------------------------------- #
def _render_midi(kind: str, name: str, seed: int) -> Path:
    """Render one demo to MIDI (no audio) and return the produced .mid path."""
    out_slug = f"_gallery_{name}"
    dest_dir = MIDI_DIR / out_slug
    shutil.rmtree(dest_dir, ignore_errors=True)

    if kind == "song":
        sp = song_path(name)
        if sp is None:
            raise FileNotFoundError(f"song '{name}' not found in {SONGS_DIR}")
        args = ["--song", str(sp)]
    else:
        _slug, payload = COOKBOOK_MODULE.resolve_recipe(name)
        args = [str(a) for a in payload.get("args", [])]

    cmd = [sys.executable, str(GENERATOR), *args,
           "--no-play", "--seed", str(seed), "--out", out_slug]
    result = subprocess.run(cmd, cwd=str(SCRIPT_DIR),
                            capture_output=True, text=True)
    if result.returncode != 0:
        tail = (result.stderr.strip().splitlines() or ["(no output)"])[-1]
        raise RuntimeError(f"render failed for {name}: {tail}")
    produced = sorted(glob.glob(str(dest_dir / "*.mid")))
    if not produced:
        raise RuntimeError(f"no MIDI produced for {name}")
    return Path(produced[-1])


def gallery(out_dir: Path, seed: int) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    ok = 0
    for kind, name in GALLERY:
        try:
            produced = _render_midi(kind, name, seed)
        except Exception as exc:  # noqa: BLE001 — report and keep going
            print(f"❌ {name}: {exc}")
            continue
        target = out_dir / f"{name}.mid"
        shutil.copyfile(produced, target)
        shutil.rmtree(produced.parent, ignore_errors=True)
        print(f"✓ {name:22} -> {target.relative_to(SCRIPT_DIR)}")
        ok += 1
    print(f"\nRendered {ok}/{len(GALLERY)} demos to {out_dir.relative_to(SCRIPT_DIR)}")
    return 0 if ok == len(GALLERY) else 1


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="The demo library: render curated songs and capability presets.")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="List all demos (songs + presets)")
    list_parser.add_argument("--verbose", action="store_true",
                             help="Show descriptions")

    show_parser = sub.add_parser("show", help="Show a demo's details")
    show_parser.add_argument("name", help="Song stem, preset name, or alias")

    make_parser = sub.add_parser("make", help="Render a demo via play_music")
    make_parser.add_argument("name", help="Song stem, preset name, or alias")
    make_parser.add_argument(
        "forward", nargs=argparse.REMAINDER,
        help="Extra args forwarded to play_music (prefix with --)")
    make_parser.add_argument(
        "--dry-run", action="store_true",
        help="Print the play_music command without executing it")

    gallery_parser = sub.add_parser(
        "gallery", help="Render the highlight set to committable MIDI")
    gallery_parser.add_argument(
        "--out-dir", default=str(GALLERY_DIR),
        help=f"Directory for the .mid files (default: {GALLERY_DIR}).")
    gallery_parser.add_argument(
        "--seed", type=int, default=1,
        help="Random seed for reproducible renders (default: 1).")

    return parser


def main(argv: list[str] | None = None) -> int:
    from datetime import datetime
    start_time = datetime.now()
    cook_song_logger.info("Starting cook_song")

    parser = build_parser()
    args = parser.parse_args(argv)
    cook_song_logger.info(
        f"Command: {args.command}, Name: {getattr(args, 'name', 'N/A')}")

    try:
        if args.command == "list":
            list_all(args.verbose)
            return 0
        if args.command == "show":
            return show(args.name)
        if args.command == "make":
            result = make(args.name, args.forward or [], args.dry_run)
            duration = (datetime.now() - start_time).total_seconds()
            log_performance(cook_song_logger, f"Cook {args.name}", duration)
            return result
        if args.command == "gallery":
            result = gallery(Path(args.out_dir), args.seed)
            duration = (datetime.now() - start_time).total_seconds()
            log_performance(cook_song_logger, "Render gallery", duration)
            return result
        parser.error("Unknown command")
    except Exception as e:
        log_error(cook_song_logger, e, f"Command: {args.command}")
        raise
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
