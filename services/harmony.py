"""
Harmony service for music generation.

Handles chord progressions, SATB voicing, and harmonic analysis.
"""

import random
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from logging_config import music_generator_logger
from .config import MusicGeneratorConfig, ChordFamily, SATBStyle


@dataclass
class ChordDef:
    """Chord definition with pitch classes and bass note."""
    root_pc: int
    pcs: tuple[int, ...]
    bass_pc: Optional[int] = None
    label: Optional[str] = None


class HarmonyService:
    """Service for harmony generation and SATB voicing."""
    
    def __init__(self, config: MusicGeneratorConfig):
        """Initialize harmony service."""
        self.config = config
        self.logger = music_generator_logger
        
        # Note to pitch class mapping
        self.NOTE_TO_PC = {
            "C": 0, "B#": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
            "E": 4, "Fb": 4, "F": 5, "E#": 5, "F#": 6, "Gb": 6, "G": 7,
            "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11, "Cb": 11,
        }
        
        # Duration mapping
        self.DUR_MAP = {
            "w": 4.0, "h": 2.0, "q": 1.0, "e": 0.5, "s": 0.25
        }
        
        # Load chord recipes
        self.chord_recipes = self._load_chord_recipes()
    
    def _load_chord_recipes(self) -> Dict[str, List[int]]:
        """Load chord recipes from library."""
        recipes_path = self.config.lib_dir / "chord_recipes.py"
        
        if not recipes_path.exists():
            self.logger.warning(f"Chord recipes file not found: {recipes_path}")
            return {}
        
        try:
            # Import chord recipes dynamically
            import importlib.util
            spec = importlib.util.spec_from_file_location("chord_recipes", recipes_path)
            chord_recipes_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(chord_recipes_module)
            
            recipes = getattr(chord_recipes_module, 'CHORD_RECIPES', {})
            self.logger.info(f"Loaded {len(recipes)} chord recipes")
            return recipes
        except Exception as e:
            self.logger.error(f"Failed to load chord recipes: {e}")
            return {}
    
    def parse_key_name(self, kname: str) -> Tuple[int, bool]:
        """Parse key name to pitch class and major/minor."""
        if kname.endswith('m'):
            return self.NOTE_TO_PC[kname[:-1]], False
        else:
            return self.NOTE_TO_PC[kname], True
    
    def get_key_roots(self) -> List[int]:
        """Get key roots based on configuration."""
        if self.config.keys:
            return [self.parse_key_name(k)[0] for k in self.config.keys]
        elif self.config.keys_preset:
            presets = self.config.load_key_presets()
            if self.config.keys_preset in presets:
                return [self.parse_key_name(k)[0] for k in presets[self.config.keys_preset]]
        
        # Default to C major
        return [0]
    
    def build_progression(self, roots: List[int], max_chords: Optional[int] = None) -> List[ChordDef]:
        """Build chord progression from roots."""
        progression = []
        chord_count = 0
        
        for root in roots:
            if max_chords and chord_count >= max_chords:
                break
                
            # Select chord family
            chord_family = self._select_chord_family()
            
            # Generate chord
            chord = self._generate_chord(root, chord_family)
            if chord:
                progression.append(chord)
                chord_count += 1
        
        self.logger.info(f"Generated progression with {len(progression)} chords")
        return progression
    
    def _select_chord_family(self) -> ChordFamily:
        """Select chord family based on configuration."""
        if self.config.chords_order == "random":
            return random.choice(self.config.chords)
        else:  # roundrobin
            # Simple round-robin implementation
            return self.config.chords[len(progression) % len(self.config.chords)]
    
    def _generate_chord(self, root: int, family: ChordFamily) -> Optional[ChordDef]:
        """Generate chord based on root and family."""
        try:
            if family == ChordFamily.TRIADS:
                return self._generate_triad(root)
            elif family == ChordFamily.SEVENTHS:
                return self._generate_seventh(root)
            elif family == ChordFamily.EXTENDED_CHORDS:
                return self._generate_extended(root)
            # Add more chord types as needed
            else:
                return self._generate_triad(root)
        except Exception as e:
            self.logger.error(f"Failed to generate {family.value} chord on root {root}: {e}")
            return None
    
    def _generate_triad(self, root: int) -> ChordDef:
        """Generate major or minor triad."""
        is_major = random.choice([True, False])
        if is_major:
            pcs = (root, (root + 4) % 12, (root + 7) % 12)
        else:
            pcs = (root, (root + 3) % 12, (root + 7) % 12)
        
        return ChordDef(root_pc=root, pcs=pcs, label=f"{self._pc_to_note(root)}{'maj' if is_major else 'min'}")
    
    def _generate_seventh(self, root: int) -> ChordDef:
        """Generate seventh chord."""
        is_major = random.choice([True, False])
        if is_major:
            pcs = (root, (root + 4) % 12, (root + 7) % 12, (root + 10) % 12)
        else:
            pcs = (root, (root + 3) % 12, (root + 7) % 12, (root + 10) % 12)
        
        return ChordDef(root_pc=root, pcs=pcs, label=f"{self._pc_to_note(root)}{'maj7' if is_major else 'min7'}")
    
    def _generate_extended(self, root: int) -> ChordDef:
        """Generate extended chord."""
        # Simplified extended chord generation
        pcs = (root, (root + 4) % 12, (root + 7) % 12, (root + 10) % 12, (root + 2) % 12)
        return ChordDef(root_pc=root, pcs=pcs, label=f"{self._pc_to_note(root)}9")
    
    def _pc_to_note(self, pc: int) -> str:
        """Convert pitch class to note name."""
        notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return notes[pc % 12]
    
    def build_satb_voicing(self, chord: ChordDef, style: SATBStyle) -> List[Tuple[float, float, int]]:
        """Build SATB voicing for chord."""
        if style == SATBStyle.BLOCK:
            return self._build_block_voicing(chord)
        elif style == SATBStyle.COUNTERPOINT:
            return self._build_counterpoint_voicing(chord)
        elif style == SATBStyle.ARPEGGIATED:
            return self._build_arpeggiated_voicing(chord)
        else:
            return self._build_block_voicing(chord)
    
    def _build_block_voicing(self, chord: ChordDef) -> List[Tuple[float, float, int]]:
        """Build block chord voicing."""
        # Simplified block voicing - distribute chord tones across SATB ranges
        satb_notes = []
        chord_tones = list(chord.pcs)
        
        # SATB ranges (MIDI note numbers)
        ranges = [(60, 84), (48, 72), (36, 60), (24, 48)]  # S, A, T, B
        
        for i, (low, high) in enumerate(ranges):
            if i < len(chord_tones):
                # Find note in range
                note = self._find_note_in_range(chord_tones[i], low, high)
                satb_notes.append((0.0, 1.0, note))  # (start, duration, note)
        
        return satb_notes
    
    def _build_counterpoint_voicing(self, chord: ChordDef) -> List[Tuple[float, float, int]]:
        """Build counterpoint voicing."""
        # Simplified counterpoint - step-wise motion
        return self._build_block_voicing(chord)  # Placeholder
    
    def _build_arpeggiated_voicing(self, chord: ChordDef) -> List[Tuple[float, float, int]]:
        """Build arpeggiated voicing."""
        # Simplified arpeggiation
        notes = []
        chord_tones = list(chord.pcs)
        
        for i, tone in enumerate(chord_tones):
            note = tone + 60  # Octave 4
            start_time = i * 0.25  # Quarter note spacing
            notes.append((start_time, 0.5, note))
        
        return notes
    
    def _find_note_in_range(self, pc: int, low: int, high: int) -> int:
        """Find note in range for given pitch class."""
        # Find octave that puts the note in range
        for octave in range(0, 10):
            note = pc + (octave * 12)
            if low <= note <= high:
                return note
        return pc + 60  # Fallback to middle C octave
