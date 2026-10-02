"""Wiring: the Telegram polling and the Redis listener, run together."""

import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from redis.asyncio import Redis

from dnspatch_telegram_bot.bot import build_dispatcher, make_sender
from dnspatch_telegram_bot.config import Settings
from dnspatch_telegram_bot.listener import listen

log = logging.getLogger(__name__)


async def run(settings: Settings) -> None:
    """Run the Telegram polling and the Redis listener until either stops."""
    if not settings.chat_ids:
        log.warning(
            "TELEGRAM_CHAT_IDS is empty: any chat that sends /subscribe to the bot gets the "
            "notifications, set TELEGRAM_CHAT_IDS to restrict them",
        )

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    bot = Bot(settings.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = build_dispatcher(redis, settings.chat_ids)

    tasks = {
        asyncio.create_task(dispatcher.start_polling(bot)),
        asyncio.create_task(
            listen(
                redis,
                make_sender(bot, redis, settings.chat_ids),
                settings.topic_prefix,
                settings.events,
            ),
        ),
    }
    try:
        # aiogram stops polling on SIGINT/SIGTERM; the listener has to follow it.
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await bot.session.close()
        await redis.aclose()
