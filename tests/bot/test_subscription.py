from fakeredis import FakeAsyncRedis

from dnspatch_telegram_bot.bot.handlers.subscription import subscribe_chat, unsubscribe_chat
from dnspatch_telegram_bot.storage.subscribers import recipients
from tests.helpers import answer, message

CONFIGURED = frozenset({1})
OPEN = frozenset[int]()


async def test_open_bot_subscribes_a_chat_and_unsubscribes_it(redis: FakeAsyncRedis) -> None:
    msg = message(7)

    await subscribe_chat(msg, redis, OPEN)
    assert answer(msg).startswith("Subscribed")
    assert await recipients(redis, OPEN) == {7}

    await subscribe_chat(msg, redis, OPEN)
    assert answer(msg) == "This chat is subscribed already"

    await unsubscribe_chat(msg, redis, OPEN)
    assert answer(msg) == "Unsubscribed"
    assert not await recipients(redis, OPEN)

    await unsubscribe_chat(msg, redis, OPEN)
    assert answer(msg) == "This chat was not subscribed"


async def test_bot_with_chat_ids_does_not_let_strangers_subscribe(redis: FakeAsyncRedis) -> None:
    msg = message(7)

    await subscribe_chat(msg, redis, CONFIGURED)
    await unsubscribe_chat(msg, redis, CONFIGURED)

    msg.answer.assert_not_awaited()
    assert await recipients(redis, OPEN) == set()


async def test_configured_chat_is_told_it_gets_the_notifications_already(
    redis: FakeAsyncRedis,
) -> None:
    msg = message(1)

    await subscribe_chat(msg, redis, CONFIGURED)
    assert "already" in answer(msg)

    await unsubscribe_chat(msg, redis, CONFIGURED)
    assert "TELEGRAM_CHAT_IDS" in answer(msg)
