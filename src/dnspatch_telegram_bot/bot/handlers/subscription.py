"""/subscribe and /unsubscribe: chats that choose to get the notifications.

With TELEGRAM_CHAT_IDS set, those chats are the only ones that get
notifications. Without it the bot is open: any chat may subscribe itself.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from redis.asyncio import Redis

from dnspatch_telegram_bot.storage.subscribers import subscribe, unsubscribe

router = Router(name="subscription")


@router.message(Command("subscribe"))
async def subscribe_chat(
    message: Message,
    redis: Redis,
    configured_chats: frozenset[int],
) -> None:
    """Subscribe the chat, if the bot is open."""
    if message.chat.id in configured_chats:
        await message.answer("This chat gets the notifications already")
    elif configured_chats:
        return
    elif await subscribe(redis, message.chat.id):
        await message.answer("Subscribed. /status shows where things stand now")
    else:
        await message.answer("This chat is subscribed already")


@router.message(Command("unsubscribe"))
async def unsubscribe_chat(
    message: Message,
    redis: Redis,
    configured_chats: frozenset[int],
) -> None:
    """Cancel the chat's subscription."""
    if message.chat.id in configured_chats:
        await message.answer("This chat is set in TELEGRAM_CHAT_IDS, it cannot unsubscribe")
    elif await unsubscribe(redis, message.chat.id):
        await message.answer("Unsubscribed")
    elif not configured_chats:
        await message.answer("This chat was not subscribed")
