#!/usr/bin/env python3
"""
Query the master catalog of generated songs.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

from logging_config import query_catalog_logger, log_function_call, log_performance, log_error

def load_catalog():
    """Load the master catalog."""
    catalog_path = Path("output/master_catalog.json")
    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("No catalog found. Generate some songs first!")
        return None
    except json.JSONDecodeError:
        print("Catalog file is corrupted.")
        return None

def list_songs(catalog, limit=10):
    """List recent songs."""
    songs = catalog.get("songs", [])
    if not songs:
        print("No songs in catalog.")
        return
    
    print(f"Found {len(songs)} songs in catalog:")
    print()
    
    for i, song in enumerate(songs[-limit:], 1):
        print(f"{i}. {song['base_name']}")
        print(f"   Generated: {song['generated_utc']}")
        print(f"   Keys: {song['keys'][:50]}{'...' if len(song['keys']) > 50 else ''}")
        print(f"   BPM: {song['bpm']}, Duration: {song['seconds']}s")
        print(f"   Instrument: {song['instrument']}")
        print(f"   MIDI: {song['midi_file']}")
        print()

def search_songs(catalog, query):
    """Search songs by various criteria."""
    songs = catalog.get("songs", [])
    if not songs:
        print("No songs in catalog.")
        return
    
    matches = []
    query_lower = query.lower()
    
    for song in songs:
        if (query_lower in song['keys'].lower() or 
            query_lower in song['base_name'].lower() or
            query_lower in song['instrument'].lower() or
            query_lower in song['out'].lower()):
            matches.append(song)
    
    if not matches:
        print(f"No songs found matching '{query}'")
        return
    
    print(f"Found {len(matches)} songs matching '{query}':")
    print()
    
    for i, song in enumerate(matches, 1):
        print(f"{i}. {song['base_name']}")
        print(f"   Generated: {song['generated_utc']}")
        print(f"   Keys: {song['keys'][:50]}{'...' if len(song['keys']) > 50 else ''}")
        print(f"   BPM: {song['bpm']}, Duration: {song['seconds']}s")
        print(f"   Instrument: {song['instrument']}")
        print(f"   MIDI: {song['midi_file']}")
        print()

def show_song_details(catalog, song_name):
    """Show detailed information about a specific song."""
    songs = catalog.get("songs", [])
    song = next((s for s in songs if song_name in s['base_name']), None)
    
    if not song:
        print(f"Song '{song_name}' not found.")
        return
    
    print(f"Song: {song['base_name']}")
    print(f"Generated: {song['generated_utc']}")
    print(f"Keys: {song['keys']}")
    print(f"BPM: {song['bpm']}")
    print(f"Duration: {song['seconds']}s")
    print(f"Instrument: {song['instrument']}")
    print(f"Output name: {song['out']}")
    print()
    print("Files:")
    print(f"  MIDI: {song['midi_file']}")
    print(f"  Audio: {song['audio_file']}")
    print(f"  Metadata: {song['metadata_file']}")
    print(f"  Manifest: {song['manifest_file']}")
    print()
    print("Full arguments:")
    args = song.get('args', {})
    for key, value in args.items():
        print(f"  {key}: {value}")

def main():
    query_catalog_logger.info("Starting catalog query")
    
    if len(sys.argv) < 2:
        print("Usage: python query_catalog.py <command> [args]")
        print("Commands:")
        print("  list [limit]     - List recent songs (default limit: 10)")
        print("  search <query>   - Search songs by keyword")
        print("  show <song_name> - Show detailed info about a song")
        print("  stats           - Show catalog statistics")
        return
    
    catalog = load_catalog()
    if not catalog:
        return
    
    command = sys.argv[1]
    
    if command == "list":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        list_songs(catalog, limit)
    
    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: python query_catalog.py search <query>")
            return
        query = " ".join(sys.argv[2:])
        search_songs(catalog, query)
    
    elif command == "show":
        if len(sys.argv) < 3:
            print("Usage: python query_catalog.py show <song_name>")
            return
        song_name = " ".join(sys.argv[2:])
        show_song_details(catalog, song_name)
    
    elif command == "stats":
        songs = catalog.get("songs", [])
        print(f"Total songs: {len(songs)}")
        print(f"Last updated: {catalog.get('last_updated', 'Never')}")
        
        if songs:
            instruments = {}
            bpms = []
            durations = []
            
            for song in songs:
                inst = song.get('instrument', 'unknown')
                instruments[inst] = instruments.get(inst, 0) + 1
                bpms.append(song.get('bpm', 0))
                durations.append(song.get('seconds', 0))
            
            print(f"Instruments used: {list(instruments.keys())}")
            print(f"BPM range: {min(bpms)}-{max(bpms)}")
            print(f"Duration range: {min(durations)}-{max(durations)}s")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
