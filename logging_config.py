"""
Centralized logging configuration for the Fluidsynth Music Generator project.
Now using the enhanced utils.logging module.
"""

import logging
import sys
from pathlib import Path

# Add utils to path for import
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.utils.logging import (
    setup_logger as _setup_logger,
    get_logger as _get_logger,
    log_function_call,
    log_performance,
    log_file_operation,
    log_music_generation,
    log_error
)

def setup_logger(name: str, log_file: str = None, level: int = None) -> logging.Logger:
    """
    Set up a logger with file and console handlers.
    Now using enhanced utils.logging with better configuration.
    
    Args:
        name: Logger name (usually __name__)
        log_file: Log file name (defaults to {name}.log)
        level: Logging level
    
    Returns:
        Configured logger
    """
    return _setup_logger(name, log_file, level)

def get_logger(name: str) -> logging.Logger:
    """Get an existing logger or create a new one."""
    return _get_logger(name)

# Pre-configured loggers for common modules using enhanced logging
music_generator_logger = setup_logger("music_generator", level=logging.INFO)
cook_song_logger = setup_logger("cook_song", level=logging.INFO)
play_music_logger = setup_logger("play_music", level=logging.INFO)
query_catalog_logger = setup_logger("query_catalog", level=logging.INFO)
cleanup_audio_logger = setup_logger("cleanup_audio", level=logging.INFO)
recreate_audio_logger = setup_logger("recreate_audio", level=logging.INFO)


