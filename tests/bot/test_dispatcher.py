from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from aiogram import Bot
from aiogram.types import Chat, Message, MessageEntity, Update, User
from fakeredis import FakeAsyncRedis

from dnspatch_telegram_bot.bot import build_dispatcher


def _command(command: str, chat_id: int) -> Update:
    return Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=datetime.now(UTC),
            chat=Chat(id=chat_id, type="private"),
            from_user=User(id=chat_id, is_bot=False, first_name="x"),
            text=command,
            entities=[MessageEntity(type="bot_command", offset=0, length=len(command))],
        ),
    )


async def test_handlers_get_redis_and_chats_from_the_dispatcher(redis: FakeAsyncRedis) -> None:
    dispatcher = build_dispatcher(redis, frozenset())
    bot = Bot("123456:TEST")

    with patch.object(Message, "answer", new=AsyncMock()) as answer:
        await dispatcher.feed_update(bot, _command("/subscribe", 7))
        await dispatcher.feed_update(bot, _command("/status", 7))

    assert [call.args[0] for call in answer.await_args_list] == [
        "Subscribed. /status shows where things stand now",
        "No events received yet",
    ]
    await bot.session.close()
