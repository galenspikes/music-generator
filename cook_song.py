#!/usr/bin/env python3
"""Convenience CLI for rendering curated song recipes with play_music."""

from __future__ import annotations

import argparse
import importlib.util
import shlex
import subprocess
import sys
from pathlib import Path

# Import enhanced utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.utils.system import run_command_safe, get_system_info
from core.utils.logging import setup_logger, log_performance, log_function_call, log_file_operation, log_error

# Setup enhanced logging
cook_song_logger = setup_logger("cook_song")


SCRIPT_DIR = Path(__file__).resolve().parent
PLAY_MUSIC = SCRIPT_DIR / "play_music"
COOKBOOK_PATH = SCRIPT_DIR / "library" / "song_cookbook.py"

if not PLAY_MUSIC.exists():
    sys.stderr.write(f"❌ play_music script not found at {PLAY_MUSIC}\n")
    sys.exit(1)

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


def list_recipes(verbose: bool) -> None:
    width = max(len(key) for key in COOKBOOK)
    for key in sorted(COOKBOOK):
        payload = COOKBOOK[key]
        title = payload.get("title", key.replace("_", " ").title())
        line = f"{key.ljust(width)}  {title}"
        if verbose:
            line += f"\n    {payload.get('description', '').strip()}"
        print(line)


def show_recipe(name: str) -> None:
    slug, payload = COOKBOOK_MODULE.resolve_recipe(name)
    title = payload.get("title", slug.replace("_", " ").title())
    description = payload.get("description", "")
    tags = payload.get("tags", [])
    aliases = payload.get("aliases", [])
    args_list = payload.get("args", [])
    print(f"Recipe: {title} ({slug})")
    if aliases:
        print(f"Aliases: {', '.join(aliases)}")
    if tags:
        print(f"Tags: {', '.join(tags)}")
    if description:
        print(f"\n{description}\n")
    print("play_music args:")
    print("  " + COOKBOOK_MODULE.format_command(args_list))


def cook_recipe(name: str, forward: list[str], dry_run: bool) -> int:
    slug, payload = COOKBOOK_MODULE.resolve_recipe(name)
    args_list = list(payload.get("args", []))
    extra = forward[:]
    if extra and extra[0] == "--":
        extra = extra[1:]
    def _has_out(seq: list[str]) -> bool:
        for idx, token in enumerate(seq):
            if token == "--out":
                return True
            # allow combined form --out=foo
            if token.startswith("--out="):
                return True
        return False

    if not _has_out(args_list) and not _has_out(extra):
        args_list = args_list + ["--out", slug]

    cmd = [str(PLAY_MUSIC)] + args_list + extra
    pretty = COOKBOOK_MODULE.format_command(cmd)
    if dry_run:
        print(pretty)
        return 0
    print(f"🍳 Cooking '{payload.get('title', slug)}'...")
    print(f"➡️  {pretty}")
    try:
        # Use enhanced system utilities for better error handling
        success, result = run_command_safe(cmd, cwd=str(SCRIPT_DIR))
        if not success:
            print(f"❌ play_music failed")
            return 1
    except Exception as exc:
        print(f"❌ play_music failed with error: {exc}")
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cook pre-configured songs using play_music recipes.")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="List available recipes")
    list_parser.add_argument("--verbose", action="store_true", help="Show descriptions")

    show_parser = sub.add_parser("show", help="Show recipe details")
    show_parser.add_argument("name", help="Recipe name or alias")

    make_parser = sub.add_parser("make", help="Render a recipe via play_music")
    make_parser.add_argument("name", help="Recipe name or alias")
    make_parser.add_argument(
        "forward",
        nargs=argparse.REMAINDER,
        help="Additional args forwarded to play_music (prefix with --)"
    )
    make_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the play_music command without executing it",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    from datetime import datetime
    start_time = datetime.now()
    cook_song_logger.info("Starting cook_song")
    
    parser = build_parser()
    args = parser.parse_args(argv)
    
    cook_song_logger.info(f"Command: {args.command}, Recipe: {getattr(args, 'name', 'N/A')}")

    try:
        if args.command == "list":
            list_recipes(args.verbose)
            cook_song_logger.info("List command completed successfully")
            return 0
        if args.command == "show":
            show_recipe(args.name)
            cook_song_logger.info(f"Show command completed for recipe: {args.name}")
            return 0
        if args.command == "make":
            forward = args.forward or []
            result = cook_recipe(args.name, forward, args.dry_run)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            log_performance(cook_song_logger, f"Cook recipe {args.name}", duration)
            cook_song_logger.info(f"Make command completed for recipe: {args.name}")
            return result

        parser.error("Unknown command")
    except Exception as e:
        log_error(cook_song_logger, e, f"Command: {args.command}")
        raise
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
