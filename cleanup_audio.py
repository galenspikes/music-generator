#!/usr/bin/env python3
# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""
Clean up WAV files to save disk space.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

from logging_config import cleanup_audio_logger, log_function_call, log_performance, log_file_operation, log_error

def get_file_size_mb(file_path):
    """Get file size in MB."""
    return os.path.getsize(file_path) / (1024 * 1024)

def get_wav_files(directory):
    """Get all WAV files in directory and subdirectories."""
    wav_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.wav'):
                full_path = os.path.join(root, file)
                wav_files.append(full_path)
    return wav_files

def get_files_older_than(directory, days):
    """Get WAV files older than specified days."""
    cutoff_date = datetime.now() - timedelta(days=days)
    old_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.wav'):
                full_path = os.path.join(root, file)
                file_time = datetime.fromtimestamp(os.path.getmtime(full_path))
                if file_time < cutoff_date:
                    old_files.append(full_path)
    
    return old_files

def format_size(size_mb):
    """Format size in human readable format."""
    if size_mb < 1024:
        return f"{size_mb:.1f} MB"
    else:
        return f"{size_mb/1024:.1f} GB"

def show_summary():
    """Show summary of WAV files in the project."""
    project_dir = Path.cwd()
    output_dir = project_dir / "output"
    
    if not output_dir.exists():
        print("❌ No output directory found")
        return None, None
    
    wav_files = get_wav_files(str(output_dir))
    
    if not wav_files:
        print("✅ No WAV files found in output directory")
        return None, None
    
    total_size = sum(get_file_size_mb(f) for f in wav_files)
    
    print("🎵 WAV File Summary")
    print("=" * 50)
    print(f"Project directory: {project_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Total WAV files: {len(wav_files)}")
    print(f"Total size: {format_size(total_size)}")
    print()
    
    # Show breakdown by subdirectory
    subdirs = {}
    for wav_file in wav_files:
        rel_path = Path(wav_file).relative_to(output_dir)
        subdir = rel_path.parts[0] if len(rel_path.parts) > 1 else "root"
        if subdir not in subdirs:
            subdirs[subdir] = []
        subdirs[subdir].append(wav_file)
    
    print("Breakdown by directory:")
    for subdir, files in subdirs.items():
        subdir_size = sum(get_file_size_mb(f) for f in files)
        print(f"  {subdir}: {len(files)} files, {format_size(subdir_size)}")
    
    print()
    return wav_files, total_size

def delete_files(files_to_delete):
    """Delete the specified files."""
    deleted_count = 0
    deleted_size = 0
    
    for file_path in files_to_delete:
        try:
            file_size = get_file_size_mb(file_path)
            os.remove(file_path)
            deleted_count += 1
            deleted_size += file_size
            print(f"✅ Deleted: {os.path.basename(file_path)} ({format_size(file_size)})")
        except Exception as e:
            print(f"❌ Failed to delete {file_path}: {e}")
    
    print(f"\n🎉 Deletion complete!")
    print(f"Files deleted: {deleted_count}")
    print(f"Space freed: {format_size(deleted_size)}")

def get_days_input():
    """Get number of days from user."""
    while True:
        try:
            days = int(input("Enter number of days (1-90): "))
            if 1 <= days <= 90:
                return days
            else:
                print("Please enter a number between 1 and 90")
        except ValueError:
            print("Please enter a valid number")

def main():
    cleanup_audio_logger.info("Starting WAV cleanup tool")
    print("🧹 WAV File Cleanup Tool")
    print("=" * 50)
    
    # Show summary
    wav_files, total_size = show_summary()
    
    if not wav_files:
        return
    
    print("CLI Menu:")
    print("1) Delete all WAV files in output/")
    print("2) Delete WAV files older than X days")
    print("3) Exit")
    print()
    
    while True:
        try:
            choice = input("Select option (1-3): ").strip()
            
            if choice == "1":
                print(f"\n⚠️  WARNING: This will delete ALL {len(wav_files)} WAV files!")
                print(f"Total size: {format_size(total_size)}")
                confirm = input("Are you sure? Type 'yes' to confirm: ").strip().lower()
                
                if confirm == 'yes':
                    delete_files(wav_files)
                    break
                else:
                    print("❌ Deletion cancelled")
                    continue
            
            elif choice == "2":
                days = get_days_input()
                old_files = get_files_older_than("output", days)
                
                if not old_files:
                    print(f"✅ No WAV files older than {days} days found")
                    continue
                
                old_size = sum(get_file_size_mb(f) for f in old_files)
                print(f"\n⚠️  WARNING: This will delete {len(old_files)} WAV files older than {days} days!")
                print(f"Total size: {format_size(old_size)}")
                confirm = input("Are you sure? Type 'yes' to confirm: ").strip().lower()
                
                if confirm == 'yes':
                    delete_files(old_files)
                    break
                else:
                    print("❌ Deletion cancelled")
                    continue
            
            elif choice == "3":
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice. Please select 1, 2, or 3")
        
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
