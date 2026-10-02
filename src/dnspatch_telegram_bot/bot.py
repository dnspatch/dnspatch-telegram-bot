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
from dnspatch_telegram_bot.subscribers import recipients, subscribe, unsubscribe

log = logging.getLogger(__name__)


def build_router(redis: Redis, configured_chats: frozenset[int]) -> Router:
    """Create the router with /start, /subscribe, /unsubscribe and /status.

    With TELEGRAM_CHAT_IDS set, those chats are the only ones that get
    notifications. Without it the bot is open: any chat may subscribe itself.
    """
    router = Router()
    is_open = not configured_chats
    _add_subscription_commands(router, redis, configured_chats)

    @router.message(Command("start"))
    async def start(message: Message) -> None:
        # Open to everyone on purpose: it is how a user learns the id to put
        # into TELEGRAM_CHAT_IDS.
        text = f"Your chat id is <code>{message.chat.id}</code>"
        if is_open:
            text += "\nSend /subscribe to get the notifications in this chat"
        await message.answer(text)

    @router.message(Command("status"))
    async def status(message: Message) -> None:
        if message.chat.id not in await recipients(redis, configured_chats):
            return

        events = await last_events(redis)
        if not events:
            await message.answer("No events received yet")
            return

        await message.answer("\n\n".join(render(event) for event in events))

    return router


def _add_subscription_commands(
    router: Router,
    redis: Redis,
    configured_chats: frozenset[int],
) -> None:
    is_open = not configured_chats

    @router.message(Command("subscribe"))
    async def subscribe_chat(message: Message) -> None:
        if message.chat.id in configured_chats:
            await message.answer("This chat gets the notifications already")
        elif not is_open:
            return
        elif await subscribe(redis, message.chat.id):
            await message.answer("Subscribed. /status shows where things stand now")
        else:
            await message.answer("This chat is subscribed already")

    @router.message(Command("unsubscribe"))
    async def unsubscribe_chat(message: Message) -> None:
        if message.chat.id in configured_chats:
            await message.answer("This chat is set in TELEGRAM_CHAT_IDS, it cannot unsubscribe")
        elif await unsubscribe(redis, message.chat.id):
            await message.answer("Unsubscribed")
        elif is_open:
            await message.answer("This chat was not subscribed")


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
