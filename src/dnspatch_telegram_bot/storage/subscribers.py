"""Chats that subscribed with /subscribe, kept in Redis next to the configured ones."""

from redis.asyncio import Redis

SUBSCRIBERS_KEY = "dnspatch-telegram-bot:chats"


async def subscribe(redis: Redis, chat_id: int) -> bool:
    """Add a chat; returns False when it was subscribed already."""
    return bool(await redis.sadd(SUBSCRIBERS_KEY, str(chat_id)))


async def unsubscribe(redis: Redis, chat_id: int) -> bool:
    """Remove a chat; returns False when it was not subscribed."""
    return bool(await redis.srem(SUBSCRIBERS_KEY, str(chat_id)))


async def recipients(redis: Redis, configured: frozenset[int]) -> frozenset[int]:
    """Return the chats that get notifications.

    The configured chats are a closed list: once there is one, earlier
    subscribers no longer get anything. Without it, the subscribed chats do.
    """
    if configured:
        return configured

    return frozenset(int(chat_id) for chat_id in await redis.smembers(SUBSCRIBERS_KEY))
