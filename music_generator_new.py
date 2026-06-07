#!/usr/bin/env python3
"""
Music Generator - Service Layer Architecture

This is the new, clean music generator using a service-based architecture.
It replaces the monolithic 2,861-line file with organized, maintainable services.

Usage:
    python music_generator_new.py --seconds 30 --out my_song
    python music_generator_new.py --seconds 60 --out rock_song --perc-main-key rock:4/4:fast
    python music_generator_new.py --seconds 120 --out classical --satb-style counterpoint
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.cli import MusicGeneratorCLI
from logging_config import music_generator_logger


def main():
    """Main entry point for music generation."""
    try:
        cli = MusicGeneratorCLI()
        return cli.main()
    except KeyboardInterrupt:
        music_generator_logger.info("Generation cancelled by user")
        return 1
    except Exception as e:
        music_generator_logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
