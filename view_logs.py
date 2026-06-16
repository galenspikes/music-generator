#!/usr/bin/env python3
# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""
View and manage log files.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

def show_log_files():
    """Show available log files."""
    log_dir = Path("log")
    if not log_dir.exists():
        print("❌ No log directory found")
        return []
    
    log_files = list(log_dir.glob("*.log"))
    if not log_files:
        print("❌ No log files found")
        return []
    
    print("📋 Available log files:")
    for i, log_file in enumerate(log_files, 1):
        size = log_file.stat().st_size
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        print(f"  {i}. {log_file.name} ({size:,} bytes, modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
    
    return log_files

def view_log(log_file, lines=50):
    """View the last N lines of a log file."""
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            print(f"\n📄 Last {len(last_lines)} lines of {log_file.name}:")
            print("=" * 80)
            for line in last_lines:
                print(line.rstrip())
    except Exception as e:
        print(f"❌ Error reading {log_file}: {e}")

def search_logs(query):
    """Search for a query across all log files."""
    log_dir = Path("log")
    if not log_dir.exists():
        print("❌ No log directory found")
        return
    
    print(f"🔍 Searching for '{query}' in all log files...")
    found = False
    
    for log_file in log_dir.glob("*.log"):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if query.lower() in line.lower():
                        if not found:
                            print(f"\n📄 Found in {log_file.name}:")
                            print("=" * 80)
                        print(f"Line {line_num}: {line.rstrip()}")
                        found = True
        except Exception as e:
            print(f"❌ Error reading {log_file}: {e}")
    
    if not found:
        print(f"❌ No matches found for '{query}'")

def main():
    if len(sys.argv) < 2:
        print("Usage: python view_logs.py <command> [args]")
        print("Commands:")
        print("  list                    - List available log files")
        print("  view <log_file> [lines] - View log file (default: 50 lines)")
        print("  search <query>          - Search across all log files")
        print("  tail <log_file>         - Follow log file in real-time")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        show_log_files()
    
    elif command == "view":
        if len(sys.argv) < 3:
            print("Usage: python view_logs.py view <log_file> [lines]")
            return
        
        log_file = Path("log") / sys.argv[2]
        if not log_file.exists():
            print(f"❌ Log file not found: {log_file}")
            return
        
        lines = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        view_log(log_file, lines)
    
    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: python view_logs.py search <query>")
            return
        
        query = " ".join(sys.argv[2:])
        search_logs(query)
    
    elif command == "tail":
        if len(sys.argv) < 3:
            print("Usage: python view_logs.py tail <log_file>")
            return
        
        log_file = Path("log") / sys.argv[2]
        if not log_file.exists():
            print(f"❌ Log file not found: {log_file}")
            return
        
        print(f"📄 Following {log_file} (Ctrl+C to stop):")
        print("=" * 80)
        
        try:
            import time
            with open(log_file, 'r', encoding='utf-8') as f:
                # Go to end of file
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        print(line.rstrip())
                    else:
                        time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n👋 Stopped following log file")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()


