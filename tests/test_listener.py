import asyncio
from unittest.mock import AsyncMock

from fakeredis import FakeAsyncRedis

from dnspatch_telegram_bot.events import KINDS
from dnspatch_telegram_bot.listener import handle_payload, last_events, listen

ALL = frozenset(KINDS)
FAILED = '{"instance": "home", "success": false, "error": "boom", "time": "2026-10-01T05:00:00Z"}'
OFFICE = '{"instance": "office", "success": true, "time": "2026-10-01T05:00:00Z"}'
CYCLE = '{"event": "cycle", "instance": "home", "success": true, "time": "2026-10-01T05:00:00Z"}'
REGRU_DOWN = (
    '{"event": "provider_status", "instance": "home", "provider": "regru", "success": false,'
    ' "error": "boom", "time": "2026-10-01T05:00:00Z"}'
)
CF_DOWN = REGRU_DOWN.replace("regru", "cloudflare")


async def test_handle_payload_stores_and_sends() -> None:
    redis = FakeAsyncRedis(decode_responses=True)
    sent: list[str] = []

    async def send(text: str) -> None:
        sent.append(text)

    await handle_payload(redis, send, FAILED, ALL)
    await handle_payload(redis, send, OFFICE, ALL)

    assert len(sent) == 2
    assert [e.instance for e in await last_events(redis)] == ["home", "office"]


async def test_handle_payload_ignores_garbage() -> None:
    redis = FakeAsyncRedis(decode_responses=True)
    sent: list[str] = []

    async def send(text: str) -> None:
        sent.append(text)

    await handle_payload(redis, send, "garbage", ALL)

    assert not sent
    assert not await last_events(redis)


async def test_events_outside_forward_are_stored_but_not_sent() -> None:
    redis = FakeAsyncRedis(decode_responses=True)
    send = AsyncMock()

    await handle_payload(redis, send, CYCLE, frozenset({"status"}))

    send.assert_not_awaited()
    assert [e.event for e in await last_events(redis)] == ["cycle"]


async def test_last_events_keeps_every_provider_and_replaces_the_same_one() -> None:
    redis = FakeAsyncRedis(decode_responses=True)
    for payload in (REGRU_DOWN, CF_DOWN, REGRU_DOWN.replace('"boom"', '"again"')):
        await handle_payload(redis, AsyncMock(), payload, ALL)

    events = await last_events(redis)

    assert [e.key for e in events] == [
        "home:provider_status:cloudflare",
        "home:provider_status:regru",
    ]
    assert getattr(events[1], "error", "") == "again"


async def test_listen_forwards_published_events() -> None:
    redis = FakeAsyncRedis(decode_responses=True)
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
