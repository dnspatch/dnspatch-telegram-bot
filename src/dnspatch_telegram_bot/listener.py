"""Subscribes to the dnspatch channels and hands events to the chat."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from dnspatch_telegram_bot.events import KINDS, Event, parse_event, render

log = logging.getLogger(__name__)

# One field per event.key; the first version kept its statuses in ...:status.
EVENTS_KEY = "dnspatch-telegram-bot:events"
RECONNECT_DELAY = 5.0

type Send = Callable[[str], Awaitable[None]]


async def handle_payload(
    redis: Redis,
    send: Send,
    payload: str | bytes,
    forward: frozenset[str],
) -> None:
    """Remember the event for /status and announce it if its type is in ``forward``."""
    try:
        event = parse_event(payload)
    except ValidationError:
        log.warning("ignoring a message that is not a dnspatch event: %r", payload)
        return

    await redis.hset(EVENTS_KEY, event.key, event.model_dump_json())
    if event.event in forward:
        await send(render(event))


async def last_events(redis: Redis) -> list[Event]:
    """Return the latest event of every kind, per instance, provider and retriever."""
    raw = await redis.hgetall(EVENTS_KEY)
    return sorted(
        (parse_event(value) for value in raw.values()),
        key=lambda e: (e.instance, KINDS.index(e.event), e.key),
    )


async def listen(redis: Redis, send: Send, prefix: str, forward: frozenset[str]) -> None:
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
                        await handle_payload(redis, send, message["data"], forward)
        except RedisError:
            log.exception("redis connection lost, retrying in %.0fs", RECONNECT_DELAY)
            await asyncio.sleep(RECONNECT_DELAY)
