from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.methods import SendMessage
from fakeredis import FakeAsyncRedis

from dnspatch_telegram_bot.bot import build_router, make_sender
from dnspatch_telegram_bot.listener import handle_payload
from dnspatch_telegram_bot.subscribers import recipients

if TYPE_CHECKING:
    from types import FunctionType

FAILED = '{"instance": "home", "success": false, "error": "boom", "time": "2026-10-01T05:00:00Z"}'
CONFIGURED = frozenset({1})
OPEN = frozenset[int]()


def _redis() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


def _command(
    name: str,
    redis: FakeAsyncRedis | None = None,
    chats: frozenset[int] = CONFIGURED,
) -> Callable[..., Awaitable[None]]:
    """Return the router's handler function of a command."""
    router = build_router(redis or _redis(), chats)
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


def _answer(message: MagicMock) -> str:
    text = message.answer.await_args.args[0]
    assert isinstance(text, str)
    return text


async def test_start_tells_the_chat_id() -> None:
    message = _message(42)

    await _command("start")(message)

    assert "<code>42</code>" in _answer(message)
    assert "/subscribe" not in _answer(message)


async def test_start_offers_to_subscribe_when_open() -> None:
    message = _message(42)

    await _command("start", chats=OPEN)(message)

    assert "/subscribe" in _answer(message)


async def test_status_ignores_strangers() -> None:
    message = _message(2)

    await _command("status")(message)

    message.answer.assert_not_awaited()


async def test_status_without_events() -> None:
    message = _message(1)

    await _command("status")(message)

    assert _answer(message) == "No events received yet"


async def test_status_lists_last_events() -> None:
    redis = _redis()
    await handle_payload(redis, AsyncMock(), FAILED, frozenset())
    message = _message(1)

    await _command("status", redis)(message)

    assert "<b>home</b>" in _answer(message)


async def test_open_bot_subscribes_a_chat_and_unsubscribes_it() -> None:
    redis = _redis()
    message = _message(7)

    await _command("subscribe_chat", redis, OPEN)(message)
    assert _answer(message).startswith("Subscribed")
    assert await recipients(redis, OPEN) == {7}

    await _command("subscribe_chat", redis, OPEN)(message)
    assert _answer(message) == "This chat is subscribed already"

    await _command("unsubscribe_chat", redis, OPEN)(message)
    assert _answer(message) == "Unsubscribed"
    assert not await recipients(redis, OPEN)

    await _command("unsubscribe_chat", redis, OPEN)(message)
    assert _answer(message) == "This chat was not subscribed"


async def test_subscribed_chat_may_ask_for_status() -> None:
    redis = _redis()
    await _command("subscribe_chat", redis, OPEN)(_message(7))
    message = _message(7)

    await _command("status", redis, OPEN)(message)

    assert _answer(message) == "No events received yet"


async def test_bot_with_chat_ids_does_not_let_strangers_subscribe() -> None:
    redis = _redis()
    message = _message(7)

    await _command("subscribe_chat", redis)(message)

    message.answer.assert_not_awaited()
    assert await recipients(redis, CONFIGURED) == CONFIGURED


async def test_configured_chat_is_told_it_is_subscribed_already() -> None:
    message = _message(1)

    await _command("subscribe_chat")(message)
    assert "already" in _answer(message)

    await _command("unsubscribe_chat")(message)
    assert "TELEGRAM_CHAT_IDS" in _answer(message)


async def test_sender_survives_an_unreachable_chat() -> None:
    bot = MagicMock(spec=Bot)
    bot.send_message = AsyncMock(
        side_effect=[TelegramAPIError(SendMessage(chat_id=1, text="x"), "no"), None],
    )

    await make_sender(bot, _redis(), frozenset({1, 2}))("hello")

    assert bot.send_message.await_count == 2


async def test_sender_reaches_subscribed_chats_when_open() -> None:
    redis = _redis()
    await _command("subscribe_chat", redis, OPEN)(_message(9))
    bot = MagicMock(spec=Bot)
    bot.send_message = AsyncMock()

    await make_sender(bot, redis, OPEN)("hello")

    assert [call.args[0] for call in bot.send_message.await_args_list] == [9]


async def test_setting_chat_ids_drops_earlier_subscribers() -> None:
    redis = _redis()
    await _command("subscribe_chat", redis, OPEN)(_message(9))
    bot = MagicMock(spec=Bot)
    bot.send_message = AsyncMock()

    await make_sender(bot, redis, CONFIGURED)("hello")

    assert [call.args[0] for call in bot.send_message.await_args_list] == [1]
