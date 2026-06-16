#!/usr/bin/env python3
# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""
Recreate WAV files from existing MIDI files using FluidSynth.
"""

import os
import subprocess
import sys
from pathlib import Path

from logging_config import recreate_audio_logger, log_function_call, log_performance, log_file_operation, log_error

def find_fluidsynth():
    """Find FluidSynth executable."""
    for path in ["/opt/homebrew/bin/fluidsynth", "/usr/local/bin/fluidsynth"]:
        if os.path.exists(path):
            return path
    
    # Try PATH
    try:
        result = subprocess.run(["which", "fluidsynth"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except OSError:
        pass

    return None

def recreate_audio(midi_file, output_file, sf2_file="SoundFonts/arachno.sf2"):
    """Recreate audio from MIDI file."""
    fluidsynth_cmd = find_fluidsynth()
    if not fluidsynth_cmd:
        print("❌ FluidSynth not found!")
        return False
    
    if not os.path.exists(sf2_file):
        print(f"❌ SoundFont not found: {sf2_file}")
        return False
    
    if not os.path.exists(midi_file):
        print(f"❌ MIDI file not found: {midi_file}")
        return False
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Run FluidSynth
    cmd = [fluidsynth_cmd, "-ni", sf2_file, midi_file, "-F", output_file]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Created: {output_file}")
            return True
        else:
            print(f"❌ Failed to create {output_file}: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error running FluidSynth: {e}")
        return False

def main():
    recreate_audio_logger.info("Starting audio recreation")
    
    if len(sys.argv) < 2:
        print("Usage: python recreate_audio.py <command>")
        print("Commands:")
        print("  all                    - Recreate all missing WAV files")
        print("  <midi_file>            - Recreate specific WAV file")
        print("  --sf2 <soundfont>      - Use specific SoundFont")
        return
    
    sf2_file = "SoundFonts/arachno.sf2"
    if "--sf2" in sys.argv:
        sf2_idx = sys.argv.index("--sf2")
        if sf2_idx + 1 < len(sys.argv):
            sf2_file = sys.argv[sf2_idx + 1]
            sys.argv = [arg for i, arg in enumerate(sys.argv) if i not in [sf2_idx, sf2_idx + 1]]
    
    if sys.argv[1] == "all":
        # Find all MIDI files and recreate missing WAVs
        midi_dir = Path("output/midi")
        audio_dir = Path("output/audio")
        
        if not midi_dir.exists():
            print("❌ No MIDI directory found")
            return
        
        midi_files = list(midi_dir.rglob("*.mid"))
        if not midi_files:
            print("❌ No MIDI files found")
            return
        
        print(f"Found {len(midi_files)} MIDI files")
        
        for midi_file in midi_files:
            # Generate corresponding WAV path
            relative_path = midi_file.relative_to(midi_dir)
            wav_file = audio_dir / relative_path.with_suffix('.wav')
            
            # Only recreate if WAV doesn't exist
            if not wav_file.exists():
                print(f"Recreating: {wav_file.name}")
                recreate_audio(str(midi_file), str(wav_file), sf2_file)
            else:
                print(f"⏭️  Skipping (exists): {wav_file.name}")
    
    else:
        # Recreate specific file
        midi_file = sys.argv[1]
        if not os.path.exists(midi_file):
            print(f"❌ MIDI file not found: {midi_file}")
            return
        
        # Generate output path
        midi_path = Path(midi_file)
        wav_file = f"output/audio/{midi_path.stem}.wav"
        
        recreate_audio(midi_file, wav_file, sf2_file)

if __name__ == "__main__":
    main()
