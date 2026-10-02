"""A Telegram bot that relays what dnspatch publishes to Redis."""

import asyncio
import logging
import os
import sys

from dnspatch_telegram_bot.app import run
from dnspatch_telegram_bot.config import ConfigError, Settings

log = logging.getLogger(__name__)


def main() -> None:
    """Run the ``dnspatch-telegram-bot`` command."""
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        settings = Settings.from_env(os.environ)
    except ConfigError as err:
        log.error("%s", err)  # noqa: TRY400 -- the message says it all, no traceback needed
        sys.exit(2)

    asyncio.run(run(settings))
