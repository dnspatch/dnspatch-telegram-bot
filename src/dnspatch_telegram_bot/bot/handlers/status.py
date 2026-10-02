"""/status: the latest events, for the chats that get the notifications."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from redis.asyncio import Redis

from dnspatch_telegram_bot.events import render
from dnspatch_telegram_bot.storage.events import last_events
from dnspatch_telegram_bot.storage.subscribers import recipients

router = Router(name="status")


@router.message(Command("status"))
async def status(message: Message, redis: Redis, configured_chats: frozenset[int]) -> None:
    """Show the latest event of every kind; strangers get no answer."""
    if message.chat.id not in await recipients(redis, configured_chats):
        return

    events = await last_events(redis)
    if not events:
        await message.answer("No events received yet")
        return

    await message.answer("\n\n".join(render(event) for event in events))
