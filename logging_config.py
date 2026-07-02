# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""
Centralized logging configuration for the music generator.

Self-contained: provides logger setup plus a handful of structured logging
helpers used across the project. (Previously this delegated to a `core.utils`
package that lived in a parent monorepo; that dependency has been inlined.)
"""

from __future__ import annotations

import logging
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "log"
DEFAULT_LEVEL = logging.INFO
_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"


def setup_logger(name: str,
                 log_file: str | None = None,
                 level: int | None = None) -> logging.Logger:
    """Set up a logger with console and (best-effort) file handlers.

    Idempotent: calling repeatedly for the same name won't stack handlers.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level or DEFAULT_LEVEL)

    if getattr(logger, "_mg_configured", False):
        return logger

    formatter = logging.Formatter(_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler is best-effort; never let logging break generation.
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(LOG_DIR / (log_file or f"{name}.log"))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        pass

    logger.propagate = False
    logger._mg_configured = True  # type: ignore[attr-defined]
    return logger


# ----- structured logging helpers -----

def log_performance(logger: logging.Logger, label: str, duration: float) -> None:
    """Log how long an operation took (seconds)."""
    logger.info("perf %s took %.3fs", label, duration)


def log_file_operation(logger: logging.Logger, operation: str, path,
                       success: bool = True) -> None:
    """Log a filesystem operation and its outcome."""
    status = "ok" if success else "FAILED"
    logger.info("file %s %s [%s]", operation, path, status)


def log_music_generation(logger: logging.Logger, name: str, seconds, bpm,
                         keys) -> None:
    """Log the parameters of a music generation run."""
    logger.info("generate name=%s seconds=%s bpm=%s keys=%s",
                name, seconds, bpm, keys)


def log_error(logger: logging.Logger, error: BaseException,
              context: str = "") -> None:
    """Log an exception with optional context."""
    suffix = f" ({context})" if context else ""
    logger.error("error: %s%s", error, suffix, exc_info=True)


# Pre-configured loggers for the modules that use them.
music_generator_logger = setup_logger("music_generator")
cook_song_logger = setup_logger("cook_song")
query_catalog_logger = setup_logger("query_catalog")
