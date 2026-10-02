from fakeredis import FakeAsyncRedis

from dnspatch_telegram_bot.events import parse_event
from dnspatch_telegram_bot.storage.events import last_events, remember
from tests.helpers import CLOUDFLARE_DOWN, CYCLE, FAILED, OFFICE, REGRU_DOWN


async def test_nothing_is_remembered_at_first(redis: FakeAsyncRedis) -> None:
    assert not await last_events(redis)


async def test_events_are_sorted_by_instance_then_kind(redis: FakeAsyncRedis) -> None:
    for payload in (OFFICE, CYCLE, FAILED):
        await remember(redis, parse_event(payload))

    assert [e.key for e in await last_events(redis)] == [
        "home:status",
        "home:cycle",
        "office:status",
    ]


async def test_every_provider_is_kept_and_the_same_one_is_replaced(
    redis: FakeAsyncRedis,
) -> None:
    for payload in (REGRU_DOWN, CLOUDFLARE_DOWN, REGRU_DOWN.replace('"boom"', '"again"')):
        await remember(redis, parse_event(payload))

    events = await last_events(redis)

    assert [e.key for e in events] == [
        "home:provider_status:cloudflare",
        "home:provider_status:regru",
    ]
    assert getattr(events[1], "error", "") == "again"
