"""
CLI service for music generation.

Handles command line interface and argument parsing.
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from logging_config import music_generator_logger, log_performance, log_music_generation
from .config import MusicGeneratorConfig, GenerationMode, SATBStyle, ChordFamily
from .harmony import HarmonyService
from .percussion import PercussionService
from .midi import MidiService
from .file_manager import FileManagerService


class MusicGeneratorCLI:
    """CLI service for music generation."""
    
    def __init__(self):
        """Initialize CLI service."""
        self.logger = music_generator_logger
    
    def create_argument_parser(self) -> argparse.ArgumentParser:
        """Create argument parser for music generation."""
        parser = argparse.ArgumentParser(
            description="Harmony + Percussion generator (independent parts, SATB, interrupters).",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python music_generator.py --seconds 30 --out my_song
  python music_generator.py --seconds 60 --out rock_song --perc-lib library/percussion_library.json --perc-main-key rock:4/4:fast
  python music_generator.py --seconds 120 --out classical --satb-style counterpoint --counterpoint-step 0.25
            """
        )
        
        # Core generation settings
        parser.add_argument("--mode",
                          choices=["complete", "mixed", "ostinato"],
                          default="mixed",
                          help="Generation mode")
        parser.add_argument("--keys",
                          type=str,
                          default=None,
                          help="Comma list of keys (Eb,Bb,...) for ostinato")
        parser.add_argument("--keys-preset",
                          type=str,
                          default=None,
                          help="Name of preset from metadata/keys_presets.json")
        parser.add_argument("--chords",
                          nargs="+",
                          default=["triads"],
                          choices=[cf.value for cf in ChordFamily],
                          help="Chord families to use")
        parser.add_argument("--chords-order",
                          choices=["random", "roundrobin"],
                          default="random",
                          help="How to pick among multiple chord families each step")
        parser.add_argument("--instrument",
                          type=str,
                          default="piano",
                          help="GM program: name alias (e.g., 'strings', 'flute') or 0–127")
        parser.add_argument("--bpm", type=int, default=120, help="Beats per minute")
        parser.add_argument("--seconds", type=int, default=30, help="Duration in seconds")
        
        # SATB settings
        parser.add_argument("--satb-style",
                          choices=[style.value for style in SATBStyle],
                          default="block",
                          help="SATB voicing style")
        parser.add_argument("--split-stems",
                          action="store_true",
                          help="Split SATB into separate tracks")
        parser.add_argument("--counterpoint-step",
                          type=float,
                          default=0.25,
                          help="Counterpoint step size")
        parser.add_argument("--counterpoint-suspension-prob",
                          type=float,
                          default=0.3,
                          help="Probability of suspensions in counterpoint")
        parser.add_argument("--counterpoint-anticipation-prob",
                          type=float,
                          default=0.2,
                          help="Probability of anticipations in counterpoint")
        parser.add_argument("--counterpoint-forced-split",
                          action="store_true",
                          help="Force voice splitting in counterpoint")
        
        # Percussion settings
        parser.add_argument("--perc-lib",
                          dest="perc_lib_path",
                          type=str,
                          default=None,
                          help="Path to percussion library JSON file")
        parser.add_argument("--perc-main-key",
                          dest="perc_main_key",
                          type=str,
                          default=None,
                          help="Main percussion pattern key")
        parser.add_argument("--perc-fill-rate",
                          type=float,
                          default=0.1,
                          help="Percussion fill rate")
        
        # Advanced settings
        parser.add_argument("--chord-length",
                          dest="chord_len",
                          choices=["w", "h", "q", "e", "s"],
                          default="e",
                          help="Chord duration")
        parser.add_argument("--chord-interrupters",
                          nargs="*",
                          default=[],
                          help='Motifs like "ec,er,sc" (multiple allowed)')
        parser.add_argument("--chord-fill-rate",
                          type=float,
                          default=0.8,
                          help="Chord fill rate")
        
        # Output settings
        parser.add_argument("--out",
                          type=str,
                          default=None,
                          help="Output filename (without extension)")
        
        return parser
    
    def run_generation(self, args: Any) -> int:
        """Run music generation with given arguments."""
        start_time = datetime.now()
        self.logger.info("Starting music generation with service layer")
        
        try:
            # Initialize configuration
            config = MusicGeneratorConfig.from_args(args)
            config.ensure_directories()
            
            # Initialize services
            harmony_service = HarmonyService(config)
            percussion_service = PercussionService(config)
            midi_service = MidiService(config)
            file_manager = FileManagerService(config)
            
            # Generate harmony
            self.logger.info("Generating harmony...")
            roots = harmony_service.get_key_roots()
            progression = harmony_service.build_progression(roots)
            
            # Generate percussion
            self.logger.info("Generating percussion...")
            perc_plan = percussion_service.build_percussion_plan()
            
            # Generate MIDI events
            self.logger.info("Generating MIDI events...")
            harmony_events = midi_service.generate_harmony_events(progression, harmony_service)
            percussion_events = midi_service.generate_percussion_events(perc_plan, percussion_service)
            
            # Create MIDI file
            self.logger.info("Creating MIDI file...")
            output_path = file_manager.get_output_path()
            success = midi_service.create_midi_file(
                harmony_events, percussion_events, output_path
            )
            
            if not success:
                self.logger.error("Failed to create MIDI file")
                return 1
            
            # Create and save metadata
            self.logger.info("Creating metadata...")
            generation_time = (datetime.now() - start_time).total_seconds()
            metadata = file_manager.create_metadata(progression, perc_plan, generation_time)
            metadata_path = file_manager.get_metadata_path()
            file_manager.save_metadata(metadata)
            file_manager.update_master_catalog(metadata_path)
            
            # Log completion
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            log_performance(self.logger, "Music generation", duration)
            log_music_generation(self.logger, config.out or "misc", config.seconds, config.bpm, config.keys or "default")
            
            print(f"✅ Generated: {output_path}")
            print(f"📊 Metadata: {metadata_path}")
            print(f"⏱️  Duration: {duration:.3f}s")
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Music generation failed: {e}")
            return 1
    
    def main(self) -> int:
        """Main CLI entry point."""
        parser = self.create_argument_parser()
        args = parser.parse_args()
        
        return self.run_generation(args)
