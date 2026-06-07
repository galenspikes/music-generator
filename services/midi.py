"""
MIDI service for music generation.

Handles MIDI file creation, track management, and event generation.
"""

import random
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
from mido import Message, MidiFile, MidiTrack, MetaMessage, bpm2tempo

from logging_config import music_generator_logger
from .config import MusicGeneratorConfig
from .harmony import HarmonyService, ChordDef
from .percussion import PercussionService, PercPlan


class MidiService:
    """Service for MIDI file generation and management."""
    
    def __init__(self, config: MusicGeneratorConfig):
        """Initialize MIDI service."""
        self.config = config
        self.logger = music_generator_logger
        
        # GM instrument aliases
        self.GM_ALIASES = {
            "piano": 0, "brightpiano": 1, "epiano": 4, "epiano2": 5,
            "organ": 16, "rockorgan": 18, "churchorgan": 19,
            "guitar": 24, "distguitar": 30, "jazzguitar": 26, "nylongt": 24,
            "bass": 32, "slapbass": 36, "synthbass": 38, "pickbass": 34,
            "strings": 48, "slowstrings": 50, "choir": 52, "vox": 54,
            "flute": 73, "clarinet": 71, "sax": 66, "trumpet": 56,
            "marimba": 12, "vibes": 11, "harpsi": 6, "lead": 80
        }
        
        # Duration mapping
        self.DUR_MAP = {
            "w": 4.0, "h": 2.0, "q": 1.0, "e": 0.5, "s": 0.25
        }
    
    def resolve_instrument(self, instrument: str) -> int:
        """Resolve instrument name to GM program number."""
        if instrument.isdigit():
            return int(instrument)
        elif instrument in self.GM_ALIASES:
            return self.GM_ALIASES[instrument]
        else:
            self.logger.warning(f"Unknown instrument: {instrument}, using piano")
            return 0
    
    def create_midi_file(self, 
                        harmony_events: List[Tuple[float, float, int]],
                        percussion_events: List[Tuple[float, int, int]],
                        output_path: Path) -> bool:
        """Create MIDI file with harmony and percussion tracks."""
        try:
            # Create MIDI file
            midi = MidiFile()
            tpb = 480  # Ticks per beat
            
            # Add tempo track
            tempo_track = MidiTrack()
            tempo_track.append(MetaMessage('set_tempo', tempo=bpm2tempo(self.config.bpm)))
            midi.tracks.append(tempo_track)
            
            # Add harmony track
            if harmony_events:
                harmony_track = self._create_harmony_track(harmony_events, tpb)
                midi.tracks.append(harmony_track)
            
            # Add percussion track
            if percussion_events:
                perc_track = self._create_percussion_track(percussion_events, tpb)
                midi.tracks.append(perc_track)
            
            # Save MIDI file
            midi.save(str(output_path))
            self.logger.info(f"Created MIDI file: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create MIDI file: {e}")
            return False
    
    def _create_harmony_track(self, events: List[Tuple[float, float, int]], tpb: int) -> MidiTrack:
        """Create harmony track from events."""
        track = MidiTrack()
        
        # Set instrument
        instrument = self.resolve_instrument(self.config.instrument)
        track.append(Message('program_change', channel=0, program=instrument))
        
        # Convert events to MIDI messages
        for start_time, duration, note in events:
            start_tick = int(start_time * tpb)
            end_tick = int((start_time + duration) * tpb)
            
            # Note on
            track.append(Message('note_on', channel=0, note=note, velocity=80, time=start_tick))
            # Note off
            track.append(Message('note_off', channel=0, note=note, velocity=0, time=end_tick - start_tick))
        
        return track
    
    def _create_percussion_track(self, events: List[Tuple[float, int, int]], tpb: int) -> MidiTrack:
        """Create percussion track from events."""
        track = MidiTrack()
        
        # Set percussion channel (channel 9)
        track.append(Message('program_change', channel=9, program=0))
        
        # Convert events to MIDI messages
        for time, note, velocity in events:
            tick = int(time * tpb)
            
            # Note on
            track.append(Message('note_on', channel=9, note=note, velocity=velocity, time=tick))
            # Note off (short duration for percussion)
            track.append(Message('note_off', channel=9, note=note, velocity=0, time=120))
        
        return track
    
    def generate_harmony_events(self, 
                               progression: List[ChordDef],
                               harmony_service: HarmonyService) -> List[Tuple[float, float, int]]:
        """Generate harmony MIDI events from chord progression."""
        events = []
        
        # Calculate timing
        chord_length = self.DUR_MAP[self.config.chord_length]
        total_beats = (self.config.seconds * self.config.bpm) / 60.0
        
        current_time = 0.0
        chord_index = 0
        
        while current_time < total_beats:
            if chord_index >= len(progression):
                chord_index = 0  # Loop progression
            
            chord = progression[chord_index]
            
            # Generate SATB voicing
            satb_notes = harmony_service.build_satb_voicing(chord, self.config.satb_style)
            
            # Convert to MIDI events
            for start_offset, duration, note in satb_notes:
                event_time = current_time + start_offset
                if event_time < total_beats:
                    events.append((event_time, duration, note))
            
            current_time += chord_length
            chord_index += 1
        
        self.logger.info(f"Generated {len(events)} harmony events")
        return events
    
    def generate_percussion_events(self, 
                                 perc_plan: Optional[PercPlan],
                                 perc_service: PercussionService) -> List[Tuple[float, int, int]]:
        """Generate percussion MIDI events from plan."""
        if not perc_plan:
            return []
        
        total_beats = (self.config.seconds * self.config.bpm) / 60.0
        return perc_service.generate_percussion_events(perc_plan, total_beats)
