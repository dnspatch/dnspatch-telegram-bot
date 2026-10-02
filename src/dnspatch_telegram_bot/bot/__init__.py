"""The Telegram side: the commands and the delivery of notifications."""

from aiogram import Dispatcher
from redis.asyncio import Redis

from dnspatch_telegram_bot.bot.handlers import router
from dnspatch_telegram_bot.bot.sender import make_sender

__all__ = ["build_dispatcher", "make_sender"]


def build_dispatcher(redis: Redis, configured_chats: frozenset[int]) -> Dispatcher:
    """Create the dispatcher; the handlers get ``redis`` and ``configured_chats`` from it."""
    dispatcher = Dispatcher(redis=redis, configured_chats=configured_chats)
    dispatcher.include_router(router)
    return dispatcher
