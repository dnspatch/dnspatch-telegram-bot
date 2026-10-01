from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.methods import SendMessage
from fakeredis import FakeAsyncRedis

from dnspatch_telegram_bot.bot import build_router, make_sender
from dnspatch_telegram_bot.listener import handle_payload

if TYPE_CHECKING:
    from types import FunctionType

FAILED = '{"instance": "home", "success": false, "error": "boom", "time": "2026-10-01T05:00:00Z"}'


def _command(name: str, redis: FakeAsyncRedis | None = None) -> Callable[..., Awaitable[None]]:
    """Return the router's handler function of a command."""
    router = build_router(redis or FakeAsyncRedis(decode_responses=True), frozenset({1}))
    return next(
        h.callback
        for h in router.message.handlers
        if cast("FunctionType", h.callback).__name__ == name
    )


def _message(chat_id: int) -> MagicMock:
    message = MagicMock()
    message.chat.id = chat_id
    message.answer = AsyncMock()
    return message


async def test_start_tells_the_chat_id() -> None:
    message = _message(42)

    await _command("start")(message)

    assert "<code>42</code>" in message.answer.await_args.args[0]


async def test_status_ignores_strangers() -> None:
    message = _message(2)

    await _command("status")(message)

    message.answer.assert_not_awaited()


async def test_status_without_events() -> None:
    message = _message(1)

    await _command("status")(message)

    assert message.answer.await_args.args[0] == "No events received yet"


async def test_status_lists_last_events() -> None:
    redis = FakeAsyncRedis(decode_responses=True)
    await handle_payload(redis, AsyncMock(), FAILED)
    message = _message(1)

    await _command("status", redis)(message)

    assert "<b>home</b>" in message.answer.await_args.args[0]


async def test_sender_survives_an_unreachable_chat() -> None:
    bot = MagicMock(spec=Bot)
    bot.send_message = AsyncMock(
        side_effect=[TelegramAPIError(SendMessage(chat_id=1, text="x"), "no"), None],
    )

    await make_sender(bot, frozenset({1, 2}))("hello")

    assert bot.send_message.await_count == 2
