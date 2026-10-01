"""Subscribes to the dnspatch channels and hands events to the chat."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from dnspatch_telegram_bot.events import Event, parse_event, render

log = logging.getLogger(__name__)

STATUS_KEY = "dnspatch-telegram-bot:status"
RECONNECT_DELAY = 5.0

type Send = Callable[[str], Awaitable[None]]


async def handle_payload(redis: Redis, send: Send, payload: str | bytes) -> None:
    """Remember the instance's last status and announce the event."""
    try:
        event = parse_event(payload)
    except ValidationError:
        log.warning("ignoring a message that is not a dnspatch event: %r", payload)
        return

    await redis.hset(STATUS_KEY, event.instance, event.model_dump_json())
    await send(render(event))


async def last_events(redis: Redis) -> list[Event]:
    """Return the last known event of every instance, sorted by name."""
    raw = await redis.hgetall(STATUS_KEY)
    return sorted((parse_event(value) for value in raw.values()), key=lambda e: e.instance)


async def listen(redis: Redis, send: Send, prefix: str) -> None:
    """Forward events forever, resubscribing after a Redis failure.

    Pub/Sub does not replay anything, so what is published while the connection
    is down is lost; that is acceptable for notifications, since dnspatch
    announces the next status flip anyway.
    """
    while True:
        try:
            async with redis.pubsub(ignore_subscribe_messages=True) as pubsub:
                await pubsub.psubscribe(f"{prefix}*")
                log.info("subscribed to %s*", prefix)
                async for message in pubsub.listen():
                    if message["type"] == "pmessage":
                        await handle_payload(redis, send, message["data"])
        except RedisError:
            log.exception("redis connection lost, retrying in %.0fs", RECONNECT_DELAY)
            await asyncio.sleep(RECONNECT_DELAY)
