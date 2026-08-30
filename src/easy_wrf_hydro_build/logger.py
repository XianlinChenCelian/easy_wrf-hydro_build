"""Logging helpers for easy_wrf_hydro_build."""

from __future__ import annotations

import logging

DEFAULT_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"


def setup_logger(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("easy_wrf_hydro_build")
    logger.setLevel(level)
    logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
    logger.addHandler(handler)
    return logger


logger = setup_logger()
