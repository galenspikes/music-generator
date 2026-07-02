#!/usr/bin/env python3
# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""
Query the master catalog of generated songs.

Each render appends an entry to ``output/master_catalog.json`` (see
``update_master_catalog`` in ``music_generator.py``). This CLI lists, searches,
inspects, and summarizes those entries.

Usage:
    python query_catalog.py list [limit]
    python query_catalog.py search <query>
    python query_catalog.py show <song_name>
    python query_catalog.py stats
"""

import json
import sys
from pathlib import Path

from logging_config import query_catalog_logger, log_error

# The catalog lives next to this script (SCRIPT_DIR/output), matching where
# music_generator writes it — so queries work regardless of the caller's CWD.
CATALOG_PATH = Path(__file__).resolve().parent / "output" / "master_catalog.json"


def load_catalog(path: Path = CATALOG_PATH):
    """Load the master catalog, returning None (with a message) if unavailable."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    except FileNotFoundError:
        print("No catalog found. Generate some songs first!")
        return None
    except json.JSONDecodeError:
        print("Catalog file is corrupted.")
        return None
    if not isinstance(catalog, dict) or not isinstance(catalog.get("songs"), list):
        print("Catalog file is malformed.")
        return None
    return catalog


def _field(song: dict, key: str, default=""):
    """Fetch a catalog field, tolerating missing keys and None values."""
    val = song.get(key, default)
    return default if val is None else val


def _print_summary(index: int, song: dict) -> None:
    keys = str(_field(song, "keys"))
    print(f"{index}. {_field(song, 'base_name', 'unknown')}")
    print(f"   Generated: {_field(song, 'generated_utc', 'unknown')}")
    print(f"   Keys: {keys[:50]}{'...' if len(keys) > 50 else ''}")
    print(f"   BPM: {_field(song, 'bpm', 0)}, Duration: {_field(song, 'seconds', 0)}s")
    print(f"   Instrument: {_field(song, 'instrument')}")
    print(f"   MIDI: {_field(song, 'midi_file')}")
    print()


def list_songs(catalog, limit=10):
    """List recent songs."""
    songs = catalog.get("songs", [])
    if not songs:
        print("No songs in catalog.")
        return

    print(f"Found {len(songs)} songs in catalog:")
    print()
    for i, song in enumerate(songs[-limit:], 1):
        _print_summary(i, song)


def search_songs(catalog, query):
    """Search songs by keys, name, instrument, or output name."""
    songs = catalog.get("songs", [])
    if not songs:
        print("No songs in catalog.")
        return

    query_lower = query.lower()
    matches = [
        song for song in songs
        if any(query_lower in str(_field(song, field)).lower()
               for field in ("keys", "base_name", "instrument", "out"))
    ]

    if not matches:
        print(f"No songs found matching '{query}'")
        return

    print(f"Found {len(matches)} songs matching '{query}':")
    print()
    for i, song in enumerate(matches, 1):
        _print_summary(i, song)


def show_song_details(catalog, song_name):
    """Show detailed information about a specific song."""
    songs = catalog.get("songs", [])
    song = next(
        (s for s in songs if song_name in str(_field(s, "base_name"))), None)

    if not song:
        print(f"Song '{song_name}' not found.")
        return

    print(f"Song: {_field(song, 'base_name', 'unknown')}")
    print(f"Generated: {_field(song, 'generated_utc', 'unknown')}")
    print(f"Keys: {_field(song, 'keys')}")
    print(f"BPM: {_field(song, 'bpm', 0)}")
    print(f"Duration: {_field(song, 'seconds', 0)}s")
    print(f"Instrument: {_field(song, 'instrument')}")
    print(f"Output name: {_field(song, 'out')}")
    print()
    print("Files:")
    print(f"  MIDI: {_field(song, 'midi_file')}")
    print(f"  Audio: {_field(song, 'audio_file')}")
    print(f"  Metadata: {_field(song, 'metadata_file')}")
    print(f"  Manifest: {_field(song, 'manifest_file')}")
    print()
    print("Full arguments:")
    args = song.get("args", {}) or {}
    for key, value in args.items():
        print(f"  {key}: {value}")


def show_stats(catalog):
    """Print aggregate catalog statistics."""
    songs = catalog.get("songs", [])
    print(f"Total songs: {len(songs)}")
    print(f"Last updated: {catalog.get('last_updated', 'Never')}")

    if songs:
        instruments = {}
        bpms = []
        durations = []
        for song in songs:
            inst = _field(song, "instrument", "unknown")
            instruments[inst] = instruments.get(inst, 0) + 1
            bpms.append(_field(song, "bpm", 0))
            durations.append(_field(song, "seconds", 0))

        print(f"Instruments used: {list(instruments.keys())}")
        print(f"BPM range: {min(bpms)}-{max(bpms)}")
        print(f"Duration range: {min(durations)}-{max(durations)}s")


def _print_usage():
    print("Usage: python query_catalog.py <command> [args]")
    print("Commands:")
    print("  list [limit]     - List recent songs (default limit: 10)")
    print("  search <query>   - Search songs by keyword")
    print("  show <song_name> - Show detailed info about a song")
    print("  stats            - Show catalog statistics")


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    query_catalog_logger.info("Starting catalog query")

    if len(argv) < 2:
        _print_usage()
        return

    catalog = load_catalog()
    if not catalog:
        return

    command = argv[1]

    if command == "list":
        try:
            limit = int(argv[2]) if len(argv) > 2 else 10
        except ValueError:
            print(f"Bad limit '{argv[2]}' — expected an integer.")
            return
        list_songs(catalog, limit)
    elif command == "search":
        if len(argv) < 3:
            print("Usage: python query_catalog.py search <query>")
            return
        search_songs(catalog, " ".join(argv[2:]))
    elif command == "show":
        if len(argv) < 3:
            print("Usage: python query_catalog.py show <song_name>")
            return
        show_song_details(catalog, " ".join(argv[2:]))
    elif command == "stats":
        show_stats(catalog)
    else:
        print(f"Unknown command: {command}")
        _print_usage()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # top-level guard: never crash on a bad catalog
        log_error(query_catalog_logger, exc, context="query_catalog")
        print(f"Error: {exc}")
        sys.exit(1)
