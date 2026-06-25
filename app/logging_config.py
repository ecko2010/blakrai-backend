"""
Structured logging configuration using loguru.

Setup:
    - stdout: human-readable colored output
    - File: JSON-structured logs with rotation
    - Intercept stdlib logging so all libraries go through loguru
"""

import sys
import os
import logging
from loguru import logger


class InterceptHandler(logging.Handler):
    """Redirect stdlib logging into loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(log_level: str = "INFO", log_dir: str = "logs"):
    """Configure loguru with stdout + rotating file sinks.

    Call this once at app startup before any other imports that use logger.
    """
    # Remove default loguru handler
    logger.remove()

    level = log_level.upper()

    # ─── 1. Stdout — colored human-readable ──────────
    logger.add(
        sys.stdout,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # ─── 2. File — JSON structured, rotated ──────────
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "blak.log")

    logger.add(
        log_path,
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        encoding="utf-8",
    )

    # ─── 3. Error-only file ──────────────────────────
    error_path = os.path.join(log_dir, "errors.log")
    logger.add(
        error_path,
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
        rotation="5 MB",
        retention="90 days",
        compression="gz",
        encoding="utf-8",
    )

    # ─── 4. Intercept stdlib loggers ─────────────────
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Redirect common library loggers
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "sqlalchemy.engine", "httpx", "aiogram"):
        logging.getLogger(name).handlers = [InterceptHandler()]
        logging.getLogger(name).propagate = False

    logger.info(f"Logging configured: level={level}, file={log_path}")
