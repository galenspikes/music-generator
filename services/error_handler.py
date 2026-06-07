"""
Error handling service for music generator operations.

This module provides specialized error handling for music generation operations,
integrating with the centralized error handling system.
"""

from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from logging_config import music_generator_logger
from core.error_handling import ErrorHandler, ErrorContext, ErrorType, ErrorSeverity, ErrorCategory

logger = music_generator_logger


class MusicGeneratorErrorHandler:
    """Specialized error handler for music generator operations."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize music generator error handler."""
        self.db_path = db_path or self._get_default_db_path()
        self.central_error_handler = ErrorHandler(self.db_path)
        
        # Register custom error handlers
        self.central_error_handler.register_error_handler(
            "music_generation", 
            self._handle_generation_error
        )
        self.central_error_handler.register_error_handler(
            "midi_processing", 
            self._handle_midi_error
        )
        self.central_error_handler.register_error_handler(
            "harmony_processing", 
            self._handle_harmony_error
        )
        
        logger.info("Music generator error handler initialized")
    
    def _get_default_db_path(self) -> Path:
        """Get default database path."""
        project_root = Path(__file__).parent.parent.parent.parent
        return project_root / "data" / "spatelier.db"
    
    def handle_generation_error(self, error_message: str, exception: Optional[Exception] = None, 
                               context_data: Optional[Dict[str, Any]] = None) -> bool:
        """Handle music generation errors."""
        context = ErrorContext(
            module="music_generator",
            function="generate_music",
            additional_data=context_data or {}
        )
        
        error_info = self.central_error_handler.handle_error(error_message, exception, context)
        
        # Log specific music generation error
        logger.error(f"Music generation error: {error_message}")
        
        return error_info.is_recoverable
    
    def handle_midi_error(self, error_message: str, exception: Optional[Exception] = None,
                         file_path: Optional[str] = None) -> bool:
        """Handle MIDI processing errors."""
        context = ErrorContext(
            module="music_generator",
            function="process_midi",
            additional_data={"file_path": file_path} if file_path else {}
        )
        
        error_info = self.central_error_handler.handle_error(error_message, exception, context)
        
        # Log specific MIDI error
        logger.error(f"MIDI processing error: {error_message}")
        
        return error_info.is_recoverable
    
    def handle_harmony_error(self, error_message: str, exception: Optional[Exception] = None,
                           chord_progression: Optional[str] = None) -> bool:
        """Handle harmony processing errors."""
        context = ErrorContext(
            module="music_generator",
            function="process_harmony",
            additional_data={"chord_progression": chord_progression} if chord_progression else {}
        )
        
        error_info = self.central_error_handler.handle_error(error_message, exception, context)
        
        # Log specific harmony error
        logger.error(f"Harmony processing error: {error_message}")
        
        return error_info.is_recoverable
    
    def _handle_generation_error(self, error_info):
        """Custom handler for music generation errors."""
        logger.warning(f"Music generation error: {error_info.message}")
        # Could implement fallback generation strategies
    
    def _handle_midi_error(self, error_info):
        """Custom handler for MIDI processing errors."""
        logger.warning(f"MIDI processing error: {error_info.message}")
        # Could implement MIDI file repair or alternative formats
    
    def _handle_harmony_error(self, error_info):
        """Custom handler for harmony processing errors."""
        logger.warning(f"Harmony processing error: {error_info.message}")
        # Could implement fallback chord progressions or simplified harmony
    
    def get_error_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get error statistics for music generator."""
        return self.central_error_handler.get_error_stats(days)
    
    def get_module_health(self) -> Dict[str, Any]:
        """Get health status for music generator module."""
        return self.central_error_handler.analytics.get_module_health("music_generator")
