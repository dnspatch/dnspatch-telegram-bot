from unittest.mock import AsyncMock

from fakeredis import FakeAsyncRedis

from dnspatch_telegram_bot.bot.handlers.status import status
from dnspatch_telegram_bot.listener import handle_payload
from dnspatch_telegram_bot.storage.subscribers import subscribe
from tests.helpers import FAILED, answer, message

CONFIGURED = frozenset({1})


async def test_ignores_strangers(redis: FakeAsyncRedis) -> None:
    msg = message(2)

    await status(msg, redis, CONFIGURED)

    msg.answer.assert_not_awaited()


async def test_without_events(redis: FakeAsyncRedis) -> None:
    msg = message(1)

    await status(msg, redis, CONFIGURED)

    assert answer(msg) == "No events received yet"


async def test_lists_last_events(redis: FakeAsyncRedis) -> None:
    await handle_payload(redis, AsyncMock(), FAILED, frozenset())
    msg = message(1)

    await status(msg, redis, CONFIGURED)

    assert "<b>home</b>" in answer(msg)


async def test_subscribed_chat_may_ask(redis: FakeAsyncRedis) -> None:
    await subscribe(redis, 7)
    msg = message(7)

    await status(msg, redis, frozenset())

    assert answer(msg) == "No events received yet"
