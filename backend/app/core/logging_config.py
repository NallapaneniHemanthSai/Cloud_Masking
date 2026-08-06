"""Logging configuration for the Cloud Masking backend (SCAFFOLD).

Provides a ``logging.config.dictConfig``-compatible dictionary and a ``setup_logging`` helper. Standard
library only — no third-party logging dependencies. Every module obtains its logger via
``logging.getLogger(__name__)``; this module only defines *how* logs are formatted and routed.

Milestone 2 scope: configuration only. Handlers write to the console; a rotating file handler is
provided but disabled by default until an ``outputs/`` log path is configured in later milestones.
"""

from __future__ import annotations

import logging
import logging.config

from app.core.constants import DEFAULT_LOG_LEVEL

#: Standard, greppable log line. Kept as a constant to avoid magic strings.
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def build_logging_config(level: str = DEFAULT_LOG_LEVEL) -> dict:
    """Return a ``dictConfig`` dictionary for the application.

    Args:
        level: Root log level name (e.g. ``"INFO"``, ``"DEBUG"``).

    Returns:
        A configuration dict suitable for :func:`logging.config.dictConfig`.
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": _LOG_FORMAT, "datefmt": _DATE_FORMAT},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "level": level,
            },
        },
        "root": {"handlers": ["console"], "level": level},
    }


def setup_logging(level: str = DEFAULT_LOG_LEVEL) -> None:
    """Apply the logging configuration process-wide.

    Args:
        level: Root log level name.
    """
    logging.config.dictConfig(build_logging_config(level))
    logging.getLogger(__name__).debug("Logging configured at level %s", level)
