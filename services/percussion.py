"""
Percussion service for music generation.

Handles drum patterns, fills, and percussion timing.
"""

import json
import random
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from logging_config import music_generator_logger
from .config import MusicGeneratorConfig


@dataclass(frozen=True)
class PercHit:
    """Percussion hit definition."""
    note: int
    vel_offset: int = 0
    probability: float = 1.0
    flam: Optional[float] = None


@dataclass(frozen=True)
class PercStage:
    """Percussion stage with main pattern and fills."""
    beats: float
    main: List[Tuple[float, List[PercHit]]]
    fills: Optional[Tuple[List[Tuple[float, List[PercHit]]], ...]] = None


@dataclass(frozen=True)
class PercPlan:
    """Complete percussion plan."""
    main: PercStage
    stages: Optional[List[PercStage]] = None
    fill_curve: Optional[List[float]] = None


class PercussionService:
    """Service for percussion pattern generation."""
    
    def __init__(self, config: MusicGeneratorConfig):
        """Initialize percussion service."""
        self.config = config
        self.logger = music_generator_logger
        
        # Default drum map
        self.drum_map = {
            "kick": 36, "snare": 38, "hihat": 42, "crash": 49,
            "ride": 51, "tom1": 48, "tom2": 45, "tom3": 41
        }
        
        # Load percussion library if available
        self.perc_library = self._load_percussion_library()
    
    def _load_percussion_library(self) -> Dict[str, Any]:
        """Load percussion library from file."""
        if not self.config.perc_lib_path or not self.config.perc_lib_path.exists():
            self.logger.warning("No percussion library specified or file not found")
            return {}
        
        try:
            with open(self.config.perc_lib_path, 'r') as f:
                library = json.load(f)
            self.logger.info(f"Loaded percussion library with {len(library)} patterns")
            return library
        except Exception as e:
            self.logger.error(f"Failed to load percussion library: {e}")
            return {}
    
    def build_percussion_plan(self) -> Optional[PercPlan]:
        """Build percussion plan from configuration."""
        if not self.config.perc_enabled:
            self.logger.info("Percussion disabled")
            return None
        
        try:
            if self.config.perc_main_key and self.perc_library:
                return self._build_from_library()
            else:
                return self._build_default_plan()
        except Exception as e:
            self.logger.error(f"Failed to build percussion plan: {e}")
            return None
    
    def _build_from_library(self) -> PercPlan:
        """Build percussion plan from library."""
        if self.config.perc_main_key not in self.perc_library:
            self.logger.warning(f"Pattern '{self.config.perc_main_key}' not found in library")
            return self._build_default_plan()
        
        pattern_data = self.perc_library[self.config.perc_main_key]
        
        # Parse pattern data
        main_pattern = self._parse_pattern(pattern_data.get('main', []))
        fills = self._parse_fills(pattern_data.get('fills', []))
        
        main_stage = PercStage(
            beats=pattern_data.get('beats', 4.0),
            main=main_pattern,
            fills=fills
        )
        
        return PercPlan(main=main_stage)
    
    def _build_default_plan(self) -> PercPlan:
        """Build default percussion plan."""
        # Simple 4/4 rock pattern
        main_pattern = [
            (0.0, [PercHit(note=self.drum_map["kick"])]),
            (0.5, [PercHit(note=self.drum_map["snare"])]),
            (1.0, [PercHit(note=self.drum_map["kick"])]),
            (1.5, [PercHit(note=self.drum_map["snare"])]),
            (2.0, [PercHit(note=self.drum_map["kick"])]),
            (2.5, [PercHit(note=self.drum_map["snare"])]),
            (3.0, [PercHit(note=self.drum_map["kick"])]),
            (3.5, [PercHit(note=self.drum_map["snare"])]),
        ]
        
        # Add hi-hat pattern
        for i in range(8):
            main_pattern.append((i * 0.25, [PercHit(note=self.drum_map["hihat"], vel_offset=-20)]))
        
        main_stage = PercStage(beats=4.0, main=main_pattern)
        return PercPlan(main=main_stage)
    
    def _parse_pattern(self, pattern_data: List[Dict]) -> List[Tuple[float, List[PercHit]]]:
        """Parse pattern data into percussion hits."""
        pattern = []
        
        for hit_data in pattern_data:
            time = hit_data.get('time', 0.0)
            hits = []
            
            for hit in hit_data.get('hits', []):
                note = hit.get('note', 36)
                vel_offset = hit.get('vel_offset', 0)
                probability = hit.get('probability', 1.0)
                flam = hit.get('flam')
                
                hits.append(PercHit(
                    note=note,
                    vel_offset=vel_offset,
                    probability=probability,
                    flam=flam
                ))
            
            pattern.append((time, hits))
        
        return pattern
    
    def _parse_fills(self, fills_data: List[Dict]) -> Optional[Tuple[List[Tuple[float, List[PercHit]]], ...]]:
        """Parse fills data."""
        if not fills_data:
            return None
        
        fills = []
        for fill_data in fills_data:
            fill_pattern = self._parse_pattern(fill_data.get('pattern', []))
            fills.append(fill_pattern)
        
        return tuple(fills) if fills else None
    
    def generate_percussion_events(self, plan: PercPlan, total_beats: float) -> List[Tuple[float, int, int]]:
        """Generate percussion MIDI events from plan."""
        events = []
        
        if not plan:
            return events
        
        # Generate main pattern events
        main_events = self._generate_stage_events(plan.main, total_beats)
        events.extend(main_events)
        
        # Generate fill events if present
        if plan.stages:
            for stage in plan.stages:
                stage_events = self._generate_stage_events(stage, total_beats)
                events.extend(stage_events)
        
        # Sort events by time
        events.sort(key=lambda x: x[0])
        
        self.logger.info(f"Generated {len(events)} percussion events")
        return events
    
    def _generate_stage_events(self, stage: PercStage, total_beats: float) -> List[Tuple[float, int, int]]:
        """Generate events for a percussion stage."""
        events = []
        
        # Repeat pattern to fill total duration
        pattern_length = stage.beats
        repetitions = int(total_beats / pattern_length) + 1
        
        for rep in range(repetitions):
            offset = rep * pattern_length
            
            for time, hits in stage.main:
                actual_time = offset + time
                if actual_time >= total_beats:
                    break
                
                for hit in hits:
                    if random.random() < hit.probability:
                        velocity = 64 + hit.vel_offset  # Base velocity + offset
                        events.append((actual_time, hit.note, velocity))
        
        return events
