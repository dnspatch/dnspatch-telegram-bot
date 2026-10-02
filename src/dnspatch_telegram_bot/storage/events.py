"""The latest event of every kind, for /status."""

from redis.asyncio import Redis

from dnspatch_telegram_bot.events import KINDS, Event, parse_event

# One field per event.key; the first version kept its statuses in ...:status.
EVENTS_KEY = "dnspatch-telegram-bot:events"


async def remember(redis: Redis, event: Event) -> None:
    """Make the event the latest word about what it describes."""
    await redis.hset(EVENTS_KEY, event.key, event.model_dump_json())


async def last_events(redis: Redis) -> list[Event]:
    """Return the latest event of every kind, per instance, provider and retriever."""
    raw = await redis.hgetall(EVENTS_KEY)
    return sorted(
        (parse_event(value) for value in raw.values()),
        key=lambda e: (e.instance, KINDS.index(e.event), e.key),
    )
