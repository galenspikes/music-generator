"""
Music Generator Service Layer

This module provides a clean, service-based architecture for the music generator,
replacing the monolithic 2,861-line file with organized, maintainable services.
"""

from .config import MusicGeneratorConfig
from .harmony import HarmonyService
from .percussion import PercussionService
from .midi import MidiService
from .file_manager import FileManagerService
from .cli import MusicGeneratorCLI

__all__ = [
    'MusicGeneratorConfig',
    'HarmonyService', 
    'PercussionService',
    'MidiService',
    'FileManagerService',
    'MusicGeneratorCLI'
]
