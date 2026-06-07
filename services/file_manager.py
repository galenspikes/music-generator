"""
File manager service for music generation.

Handles output file management, metadata generation, and file operations.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from logging_config import music_generator_logger, log_file_operation
from .config import MusicGeneratorConfig


class FileManagerService:
    """Service for file management and metadata generation."""
    
    def __init__(self, config: MusicGeneratorConfig):
        """Initialize file manager service."""
        self.config = config
        self.logger = music_generator_logger
    
    def ensure_output_directories(self):
        """Ensure all output directories exist."""
        self.config.ensure_directories()
        self.logger.info("Output directories ensured")
    
    def get_output_path(self) -> Path:
        """Get the output MIDI file path."""
        return self.config.get_output_path()
    
    def get_metadata_path(self) -> Path:
        """Get the metadata file path."""
        return self.config.get_metadata_path()
    
    def create_metadata(self, 
                       progression: list,
                       percussion_plan: Optional[Any],
                       generation_time: float) -> Dict[str, Any]:
        """Create metadata for the generated music."""
        metadata = {
            "generation_info": {
                "timestamp": datetime.now().isoformat(),
                "generation_time_seconds": generation_time,
                "config": {
                    "mode": self.config.mode.value,
                    "keys": self.config.keys,
                    "keys_preset": self.config.keys_preset,
                    "chords": [c.value for c in self.config.chords],
                    "chords_order": self.config.chords_order,
                    "instrument": self.config.instrument,
                    "bpm": self.config.bpm,
                    "seconds": self.config.seconds,
                    "satb_style": self.config.satb_style.value,
                    "split_stems": self.config.split_stems,
                    "counterpoint_step": self.config.counterpoint_step,
                    "perc_enabled": self.config.perc_enabled,
                    "perc_main_key": self.config.perc_main_key,
                    "chord_length": self.config.chord_length,
                    "chord_fill_rate": self.config.chord_fill_rate
                }
            },
            "musical_content": {
                "progression_length": len(progression),
                "chord_progression": [
                    {
                        "root_pc": chord.root_pc,
                        "pcs": list(chord.pcs),
                        "bass_pc": chord.bass_pc,
                        "label": chord.label
                    } for chord in progression
                ],
                "percussion_enabled": self.config.perc_enabled,
                "percussion_plan": self._serialize_percussion_plan(percussion_plan)
            },
            "technical_info": {
                "script_version": "2.0.0",
                "service_architecture": True,
                "refactored": True
            }
        }
        
        return metadata
    
    def _serialize_percussion_plan(self, perc_plan: Optional[Any]) -> Optional[Dict[str, Any]]:
        """Serialize percussion plan for metadata."""
        if not perc_plan:
            return None
        
        return {
            "main_beats": perc_plan.main.beats if hasattr(perc_plan, 'main') else None,
            "has_fills": bool(perc_plan.main.fills if hasattr(perc_plan, 'main') else None),
            "stages_count": len(perc_plan.stages) if hasattr(perc_plan, 'stages') and perc_plan.stages else 0
        }
    
    def save_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Save metadata to JSON file."""
        try:
            metadata_path = self.get_metadata_path()
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            log_file_operation(self.logger, "write", metadata_path, True)
            self.logger.info(f"Saved metadata: {metadata_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")
            return False
    
    def update_master_catalog(self, metadata_path: Path):
        """Update master catalog with new generation."""
        try:
            catalog_path = self.config.meta_dir / "master_catalog.json"
            
            # Load existing catalog
            if catalog_path.exists():
                with open(catalog_path, 'r') as f:
                    catalog = json.load(f)
            else:
                catalog = {"generations": []}
            
            # Add new entry
            entry = {
                "timestamp": datetime.now().isoformat(),
                "midi_file": self.get_output_path().name,
                "metadata_file": metadata_path.name,
                "config_summary": {
                    "mode": self.config.mode.value,
                    "bpm": self.config.bpm,
                    "seconds": self.config.seconds,
                    "instrument": self.config.instrument
                }
            }
            
            catalog["generations"].append(entry)
            
            # Save updated catalog
            with open(catalog_path, 'w') as f:
                json.dump(catalog, f, indent=2)
            
            self.logger.info(f"Updated master catalog: {catalog_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to update master catalog: {e}")
    
    def cleanup_old_files(self, days: int = 30) -> int:
        """Clean up old generated files."""
        try:
            cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
            cleaned_count = 0
            
            # Clean up MIDI files
            for midi_file in self.config.midi_dir.glob("*.mid"):
                if midi_file.stat().st_mtime < cutoff_time:
                    midi_file.unlink()
                    cleaned_count += 1
            
            # Clean up metadata files
            for meta_file in self.config.meta_dir.glob("*.json"):
                if meta_file.name != "master_catalog.json" and meta_file.stat().st_mtime < cutoff_time:
                    meta_file.unlink()
                    cleaned_count += 1
            
            self.logger.info(f"Cleaned up {cleaned_count} old files")
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old files: {e}")
            return 0
