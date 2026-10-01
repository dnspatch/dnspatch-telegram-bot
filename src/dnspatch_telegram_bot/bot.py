"""The Telegram side: the commands and delivery of notifications."""

import logging
from collections.abc import Awaitable, Callable

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Message
from redis.asyncio import Redis

from dnspatch_telegram_bot.events import render
from dnspatch_telegram_bot.listener import last_events

log = logging.getLogger(__name__)


def build_router(redis: Redis, allowed_chats: frozenset[int]) -> Router:
    """Create the router with /start and /status."""
    router = Router()

    @router.message(Command("start"))
    async def start(message: Message) -> None:
        # Open to everyone on purpose: it is how a user learns the id to put
        # into TELEGRAM_CHAT_IDS.
        await message.answer(f"Your chat id is <code>{message.chat.id}</code>")

    @router.message(Command("status"))
    async def status(message: Message) -> None:
        if message.chat.id not in allowed_chats:
            return

        events = await last_events(redis)
        if not events:
            await message.answer("No events received yet")
            return

        await message.answer("\n\n".join(render(event) for event in events))

    return router


def make_sender(bot: Bot, chat_ids: frozenset[int]) -> Callable[[str], Awaitable[None]]:
    """Return a coroutine that sends a text to every allowed chat."""

    async def send(text: str) -> None:
        for chat_id in chat_ids:
            try:
                await bot.send_message(chat_id, text)
            except TelegramAPIError:
                # One unreachable chat must not stop the others.
                log.exception("cannot deliver to chat %d", chat_id)

    return send
