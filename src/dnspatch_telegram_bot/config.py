"""Settings read from the environment."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Self

from dnspatch_telegram_bot.events import KINDS

DEFAULT_REDIS_URL = "redis://redis:6379/0"
DEFAULT_TOPIC_PREFIX = "dnspatch.events."
# A cycle is reported every interval: fine for /status, too noisy for a chat.
DEFAULT_EVENTS = frozenset(KINDS) - {"cycle"}


class ConfigError(Exception):
    """The environment does not describe a usable configuration."""


@dataclass(frozen=True, slots=True)
class Settings:
    """What the bot needs to run."""

    token: str
    chat_ids: frozenset[int]
    redis_url: str
    topic_prefix: str
    events: frozenset[str]

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Self:
        """Build settings from environment variables, failing with a readable message."""
        token = env.get("TELEGRAM_TOKEN", "").strip()
        if not token:
            msg = "TELEGRAM_TOKEN is not set"
            raise ConfigError(msg)

        return cls(
            token=token,
            chat_ids=_parse_chat_ids(env.get("TELEGRAM_CHAT_IDS", "")),
            redis_url=env.get("REDIS_URL", DEFAULT_REDIS_URL),
            topic_prefix=env.get("TOPIC_PREFIX", DEFAULT_TOPIC_PREFIX),
            events=_parse_events(env.get("EVENTS", "")),
        )


def _parse_events(raw: str) -> frozenset[str]:
    names = frozenset(part.strip() for part in raw.split(",") if part.strip())
    unknown = names - set(KINDS)
    if unknown:
        msg = f"EVENTS: unknown {', '.join(sorted(unknown))}; valid are {', '.join(KINDS)}"
        raise ConfigError(msg)

    return names or DEFAULT_EVENTS


def _parse_chat_ids(raw: str) -> frozenset[int]:
    ids: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        item = part.strip()
        if not item:
            continue
        try:
            ids.add(int(item))
        except ValueError:
            msg = f"TELEGRAM_CHAT_IDS: {item!r} is not an integer chat id"
            raise ConfigError(msg) from None

    return frozenset(ids)
