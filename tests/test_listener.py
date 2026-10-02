import asyncio
from unittest.mock import AsyncMock

from fakeredis import FakeAsyncRedis

from dnspatch_telegram_bot.events import KINDS
from dnspatch_telegram_bot.listener import handle_payload, listen
from dnspatch_telegram_bot.storage.events import last_events
from tests.helpers import CYCLE, FAILED, OFFICE

ALL = frozenset(KINDS)


async def test_handle_payload_stores_and_sends(redis: FakeAsyncRedis) -> None:
    send = AsyncMock()

    await handle_payload(redis, send, FAILED, ALL)
    await handle_payload(redis, send, OFFICE, ALL)

    assert send.await_count == 2
    assert [e.instance for e in await last_events(redis)] == ["home", "office"]


async def test_handle_payload_ignores_garbage(redis: FakeAsyncRedis) -> None:
    send = AsyncMock()

    await handle_payload(redis, send, "garbage", ALL)

    send.assert_not_awaited()
    assert not await last_events(redis)


async def test_events_outside_forward_are_stored_but_not_sent(redis: FakeAsyncRedis) -> None:
    send = AsyncMock()

    await handle_payload(redis, send, CYCLE, frozenset({"status"}))

    send.assert_not_awaited()
    assert [e.event for e in await last_events(redis)] == ["cycle"]


async def test_listen_forwards_published_events(redis: FakeAsyncRedis) -> None:
    sent: asyncio.Queue[str] = asyncio.Queue()

    listener = asyncio.create_task(listen(redis, sent.put, "dnspatch.events.", ALL))
    try:
        # Pub/Sub drops what is published before the subscription exists, so
        # publish until the listener has caught one.
        async with asyncio.timeout(5):
            while sent.empty():
                await redis.publish("dnspatch.events.home", FAILED)
                await asyncio.sleep(0.05)
    finally:
        listener.cancel()
        await asyncio.gather(listener, return_exceptions=True)

    assert (await sent.get()).startswith("🔴 <b>home</b>")
