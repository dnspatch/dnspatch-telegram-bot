"""Delivery of notifications to the chats."""

import logging
from collections.abc import Awaitable, Callable

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from redis.asyncio import Redis

from dnspatch_telegram_bot.storage.subscribers import recipients

log = logging.getLogger(__name__)


def make_sender(
    bot: Bot,
    redis: Redis,
    configured_chats: frozenset[int],
) -> Callable[[str], Awaitable[None]]:
    """Return a coroutine that sends a text to every configured and subscribed chat."""

    async def send(text: str) -> None:
        for chat_id in await recipients(redis, configured_chats):
            try:
                await bot.send_message(chat_id, text)
            except TelegramAPIError:
                # One unreachable chat must not stop the others.
                log.exception("cannot deliver to chat %d", chat_id)

    return send
