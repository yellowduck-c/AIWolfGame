from __future__ import annotations

import logging

from config import settings

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging() -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.setLevel(_resolve_log_level())
        return

    logging.basicConfig(level=_resolve_log_level(), format=LOG_FORMAT)


def _resolve_log_level() -> int:
    return getattr(logging, settings.log_level.upper(), logging.INFO)
