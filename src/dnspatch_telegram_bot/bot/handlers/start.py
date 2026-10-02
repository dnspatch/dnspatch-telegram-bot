"""/start: tells the chat its id."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="start")


@router.message(Command("start"))
async def start(message: Message, configured_chats: frozenset[int]) -> None:
    """Reply with the chat id, to put into TELEGRAM_CHAT_IDS.

    Open to everyone on purpose: it is how a user learns that id.
    """
    text = f"Your chat id is <code>{message.chat.id}</code>"
    if not configured_chats:
        text += "\nSend /subscribe to get the notifications in this chat"
    await message.answer(text)
