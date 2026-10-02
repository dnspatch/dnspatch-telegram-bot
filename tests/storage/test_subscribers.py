from fakeredis import FakeAsyncRedis

from dnspatch_telegram_bot.storage.subscribers import recipients, subscribe, unsubscribe

OPEN = frozenset[int]()


async def test_subscribe_and_unsubscribe_say_whether_anything_changed(
    redis: FakeAsyncRedis,
) -> None:
    assert await subscribe(redis, 7)
    assert not await subscribe(redis, 7)
    assert await unsubscribe(redis, 7)
    assert not await unsubscribe(redis, 7)


async def test_subscribers_are_the_recipients_when_nothing_is_configured(
    redis: FakeAsyncRedis,
) -> None:
    await subscribe(redis, 7)
    await subscribe(redis, -100)

    assert await recipients(redis, OPEN) == {7, -100}


async def test_configured_chats_are_a_closed_list(redis: FakeAsyncRedis) -> None:
    await subscribe(redis, 7)

    assert await recipients(redis, frozenset({1})) == {1}
