import asyncio

from fakeredis import FakeAsyncRedis

from dnspatch_telegram_bot.listener import handle_payload, last_events, listen

FAILED = '{"instance": "home", "success": false, "error": "boom", "time": "2026-10-01T05:00:00Z"}'
OFFICE = '{"instance": "office", "success": true, "time": "2026-10-01T05:00:00Z"}'


async def test_handle_payload_stores_and_sends() -> None:
    redis = FakeAsyncRedis(decode_responses=True)
    sent: list[str] = []

    async def send(text: str) -> None:
        sent.append(text)

    await handle_payload(redis, send, FAILED)
    await handle_payload(redis, send, OFFICE)

    assert len(sent) == 2
    assert [e.instance for e in await last_events(redis)] == ["home", "office"]


async def test_handle_payload_ignores_garbage() -> None:
    redis = FakeAsyncRedis(decode_responses=True)
    sent: list[str] = []

    async def send(text: str) -> None:
        sent.append(text)

    await handle_payload(redis, send, "garbage")

    assert not sent
    assert not await last_events(redis)


async def test_listen_forwards_published_events() -> None:
    redis = FakeAsyncRedis(decode_responses=True)
    sent: asyncio.Queue[str] = asyncio.Queue()

    listener = asyncio.create_task(listen(redis, sent.put, "dnspatch.events."))
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
