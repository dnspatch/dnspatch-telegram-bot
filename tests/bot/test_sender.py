from unittest.mock import AsyncMock, MagicMock

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.methods import SendMessage
from fakeredis import FakeAsyncRedis

from dnspatch_telegram_bot.bot import make_sender
from dnspatch_telegram_bot.storage.subscribers import subscribe


def _bot(side_effect: list[object] | None = None) -> MagicMock:
    bot = MagicMock(spec=Bot)
    bot.send_message = AsyncMock(side_effect=side_effect)
    return bot


def _chats(bot: MagicMock) -> list[int]:
    return [call.args[0] for call in bot.send_message.await_args_list]


async def test_survives_an_unreachable_chat(redis: FakeAsyncRedis) -> None:
    bot = _bot([TelegramAPIError(SendMessage(chat_id=1, text="x"), "no"), None])

    await make_sender(bot, redis, frozenset({1, 2}))("hello")

    assert bot.send_message.await_count == 2


async def test_reaches_subscribed_chats_when_open(redis: FakeAsyncRedis) -> None:
    await subscribe(redis, 9)
    bot = _bot()

    await make_sender(bot, redis, frozenset())("hello")

    assert _chats(bot) == [9]


async def test_setting_chat_ids_drops_earlier_subscribers(redis: FakeAsyncRedis) -> None:
    await subscribe(redis, 9)
    bot = _bot()

    await make_sender(bot, redis, frozenset({1}))("hello")

    assert _chats(bot) == [1]
