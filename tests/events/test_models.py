import pytest
from pydantic import ValidationError

from dnspatch_telegram_bot.events import (
    Cycle,
    IpChange,
    Lifecycle,
    ProviderStatus,
    RetrieverStatus,
    Status,
    parse_event,
)
from tests.helpers import CYCLE, FAILED, RECOVERED, payload


def test_message_without_event_is_a_status_of_0_4_0() -> None:
    assert isinstance(parse_event(FAILED), Status)


def test_status_carries_the_fields_added_later() -> None:
    event = parse_event(payload("status", '"state": "recovery", "success": true'))

    assert isinstance(event, Status)
    assert event.success


def test_parse_accepts_bytes() -> None:
    assert parse_event(RECOVERED.encode()).event == "status"


def test_parse_rejects_garbage() -> None:
    with pytest.raises(ValidationError):
        parse_event("not json")


def test_parse_rejects_an_unknown_type() -> None:
    with pytest.raises(ValidationError):
        parse_event(payload("from_the_future", '"success": true'))


def test_every_type_gets_its_model() -> None:
    bodies = {
        "provider_status": ('"provider": "regru", "success": true', ProviderStatus),
        "retriever_status": ('"retriever": "ifconfig", "success": true', RetrieverStatus),
        "ip_change": ('"changes": []', IpChange),
        "lifecycle": ('"state": "started"', Lifecycle),
    }

    for name, (body, model) in bodies.items():
        assert isinstance(parse_event(payload(name, body)), model)
    assert isinstance(parse_event(CYCLE), Cycle)


def test_provider_and_retriever_are_part_of_the_key() -> None:
    provider = parse_event(payload("provider_status", '"provider": "regru", "success": true'))
    retriever = parse_event(payload("retriever_status", '"retriever": "ifconfig", "success": true'))

    assert provider.key == "home:provider_status:regru"
    assert retriever.key == "home:retriever_status:ifconfig"
    assert parse_event(CYCLE).key == "home:cycle"
