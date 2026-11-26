"""Privacy-conscious process logging setup."""

import logging

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure standard-library logging without logging configuration secrets."""

    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
