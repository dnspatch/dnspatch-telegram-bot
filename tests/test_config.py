import pytest

from dnspatch_telegram_bot.config import ConfigError, Settings


def test_defaults_and_chat_ids() -> None:
    settings = Settings.from_env({"TELEGRAM_TOKEN": "t", "TELEGRAM_CHAT_IDS": "1, -2;3"})

    assert settings.chat_ids == {1, -2, 3}
    assert settings.redis_url == "redis://redis:6379/0"
    assert settings.topic_prefix == "dnspatch.events."
    assert settings.events == {
        "status",
        "provider_status",
        "retriever_status",
        "ip_change",
        "lifecycle",
    }


def test_events_choose_what_goes_to_the_chat() -> None:
    settings = Settings.from_env({"TELEGRAM_TOKEN": "t", "EVENTS": "status, cycle"})

    assert settings.events == {"status", "cycle"}


def test_unknown_event_is_reported_with_the_valid_ones() -> None:
    with pytest.raises(ConfigError, match=r"unknown nope; valid are status,"):
        Settings.from_env({"TELEGRAM_TOKEN": "t", "EVENTS": "status,nope"})


def test_overrides() -> None:
    settings = Settings.from_env(
        {
            "TELEGRAM_TOKEN": "t",
            "TELEGRAM_CHAT_IDS": "1",
            "REDIS_URL": "redis://other:6379/1",
            "TOPIC_PREFIX": "x.",
        },
    )

    assert settings.redis_url == "redis://other:6379/1"
    assert settings.topic_prefix == "x."


@pytest.mark.parametrize(
    ("env", "fragment"),
    [
        ({"TELEGRAM_CHAT_IDS": "1"}, "TELEGRAM_TOKEN"),
        ({"TELEGRAM_TOKEN": "t", "TELEGRAM_CHAT_IDS": "abc"}, "'abc'"),
    ],
)
def test_invalid(env: dict[str, str], fragment: str) -> None:
    with pytest.raises(ConfigError, match=fragment):
        Settings.from_env(env)


def test_chat_ids_may_be_empty_until_the_user_learns_theirs() -> None:
    assert not Settings.from_env({"TELEGRAM_TOKEN": "t"}).chat_ids
