"""
Configuration service for music generator - Enhanced with Centralized Config.

Centralizes all configuration management, presets, and settings with integration
to the global configuration system for unified settings management.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from logging_config import music_generator_logger
from core.config import get_config


class GenerationMode(Enum):
    """Music generation modes."""
    COMPLETE = "complete"
    MIXED = "mixed" 
    OSTINATO = "ostinato"


class SATBStyle(Enum):
    """SATB voicing styles."""
    BLOCK = "block"
    COUNTERPOINT = "counterpoint"
    ARPEGGIATED = "arpeggiated"


class ChordFamily(Enum):
    """Available chord families."""
    CHROMATIC_MEDIANTS = "chromatic-mediants"
    EXTENDED_CHORDS = "extended-chords"
    TRIADS = "triads"
    SEVENTHS = "sevenths"
    NINTHS = "ninths"
    QUARTAL = "quartal"
    SUS = "sus"
    ADD6 = "add6"
    LYD_DOM = "lyd-dom"


@dataclass
class MusicGeneratorConfig:
    """Centralized configuration for music generation."""
    
    # Core settings
    mode: GenerationMode = GenerationMode.MIXED
    keys: Optional[List[str]] = None
    keys_preset: Optional[str] = None
    chords: List[ChordFamily] = field(default_factory=lambda: [ChordFamily.TRIADS])
    chords_order: str = "random"
    instrument: str = "piano"
    bpm: int = 120
    seconds: int = 30
    
    # SATB settings
    satb_style: SATBStyle = SATBStyle.BLOCK
    split_stems: bool = False
    counterpoint_step: float = 0.25
    counterpoint_suspension_prob: float = 0.3
    counterpoint_anticipation_prob: float = 0.2
    counterpoint_forced_split: bool = False
    
    # Percussion settings
    perc_enabled: bool = False
    perc_lib_path: Optional[Path] = None
    perc_main_key: Optional[str] = None
    perc_fill_rate: float = 0.1
    
    # File paths
    script_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    output_dir: Optional[Path] = None
    audio_dir: Optional[Path] = None
    meta_dir: Optional[Path] = None
    midi_dir: Optional[Path] = None
    lib_dir: Optional[Path] = None
    
    # Advanced settings
    chord_length: str = "e"
    chord_interrupters: List[str] = field(default_factory=list)
    chord_fill_rate: float = 0.8
    out: Optional[str] = None
    
    def __post_init__(self):
        """Initialize derived paths and settings with centralized config integration."""
        # Get centralized configuration
        config = get_config()
        
        # Load settings from centralized config
        self._load_from_centralized_config(config)
        
        # Set default paths if not configured
        if self.output_dir is None:
            self.output_dir = self.script_dir / "output"
        if self.audio_dir is None:
            self.audio_dir = self.output_dir / "audio"
        if self.meta_dir is None:
            self.meta_dir = self.output_dir / "metadata"
        if self.midi_dir is None:
            self.midi_dir = self.output_dir / "midi"
        if self.lib_dir is None:
            self.lib_dir = self.script_dir / "library"
    
    def _load_from_centralized_config(self, config):
        """Load configuration from centralized config system."""
        try:
            # Load music generator specific settings
            music_config = config.get_section('modules', {}).get('music_generator', {})
            if music_config:
                if music_config.get('output_dir'):
                    self.output_dir = Path(music_config['output_dir'])
                self.bpm = music_config.get('bpm', self.bpm)
                self.seconds = music_config.get('max_duration', self.seconds)
                self.instrument = music_config.get('instrument', self.instrument)
            
            # Load system settings
            system_config = config.get_section('system')
            if system_config:
                if system_config.get('temp_dir'):
                    temp_dir = Path(system_config['temp_dir'])
                    self.output_dir = temp_dir / "music_generator"
            
            logger.info("Loaded music generator configuration from centralized config system")
            
        except Exception as e:
            logger.warning(f"Failed to load from centralized config: {e}, using defaults")
    
    @classmethod
    def from_args(cls, args) -> 'MusicGeneratorConfig':
        """Create config from command line arguments."""
        return cls(
            mode=GenerationMode(args.mode),
            keys=args.keys.split(',') if args.keys else None,
            keys_preset=args.keys_preset,
            chords=[ChordFamily(c) for c in args.chords],
            chords_order=args.chords_order,
            instrument=args.instrument,
            bpm=args.bpm,
            seconds=args.seconds,
            satb_style=SATBStyle(args.satb_style),
            split_stems=args.split_stems,
            counterpoint_step=args.counterpoint_step,
            counterpoint_suspension_prob=args.counterpoint_suspension_prob,
            counterpoint_anticipation_prob=args.counterpoint_anticipation_prob,
            counterpoint_forced_split=args.counterpoint_forced_split,
            perc_enabled=bool(args.perc_lib_path or args.perc_main_key),
            perc_lib_path=Path(args.perc_lib_path) if args.perc_lib_path else None,
            perc_main_key=args.perc_main_key,
            perc_fill_rate=args.perc_fill_rate,
            chord_length=args.chord_len,
            chord_interrupters=args.chord_interrupters or [],
            chord_fill_rate=args.chord_fill_rate,
            out=args.out
        )
    
    def ensure_directories(self):
        """Ensure all required directories exist."""
        for directory in [self.output_dir, self.audio_dir, self.meta_dir, 
                          self.midi_dir, self.lib_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            music_generator_logger.debug(f"Ensured directory exists: {directory}")
    
    def load_key_presets(self, force_reload: bool = False) -> Dict[str, List[str]]:
        """Load key presets from JSON file."""
        presets_path = self.lib_dir / "keys_presets.json"
        
        if not presets_path.exists():
            music_generator_logger.warning(f"Key presets file not found: {presets_path}")
            return {}
        
        try:
            with open(presets_path, 'r') as f:
                presets = json.load(f)
            music_generator_logger.info(f"Loaded {len(presets)} key presets")
            return presets
        except Exception as e:
            music_generator_logger.error(f"Failed to load key presets: {e}")
            return {}
    
    def get_output_path(self) -> Path:
        """Get the output file path."""
        if self.out:
            return self.midi_dir / f"{self.out}.mid"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return self.midi_dir / f"generated_{timestamp}.mid"
    
    def get_metadata_path(self) -> Path:
        """Get the metadata file path."""
        output_path = self.get_output_path()
        return self.meta_dir / f"{output_path.stem}.json"
