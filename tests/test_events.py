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
    render,
)

TIME = '"time": "2026-10-01T05:00:00Z"'
FAILED = '{"instance": "home", "success": false, "error": "a<b", ' + TIME + "}"
RECOVERED = '{"instance": "home", "success": true, "time": "2026-10-01T05:05:00Z"}'


def _event(event: str, body: str) -> str:
    return f'{{"event": "{event}", "severity": "info", "instance": "home", {body}, {TIME}}}'


def test_render_failure_escapes_html() -> None:
    text = render(parse_event(FAILED))

    assert text.startswith("🔴 <b>home</b>")
    assert "<code>a&lt;b</code>" in text
    assert "2026-10-01 05:00:00 UTC" in text


def test_render_recovery() -> None:
    assert render(parse_event(RECOVERED)).startswith("🟢 <b>home</b> is back to normal")


def test_message_without_event_is_a_status_of_0_4_0() -> None:
    assert isinstance(parse_event(FAILED), Status)


def test_status_carries_the_fields_added_later() -> None:
    payload = _event("status", '"state": "recovery", "success": true')

    assert render(parse_event(payload)).startswith("🟢 <b>home</b> is back to normal")


def test_parse_accepts_bytes() -> None:
    assert parse_event(RECOVERED.encode()).event == "status"


def test_parse_rejects_garbage() -> None:
    with pytest.raises(ValidationError):
        parse_event("not json")


def test_parse_rejects_an_unknown_type() -> None:
    with pytest.raises(ValidationError):
        parse_event(_event("from_the_future", '"success": true'))


def test_provider_status() -> None:
    failed = parse_event(
        _event("provider_status", '"provider": "regru", "success": false, "error": "500"'),
    )
    back = parse_event(_event("provider_status", '"provider": "regru", "success": true'))

    assert isinstance(failed, ProviderStatus)
    assert failed.key == "home:provider_status:regru"
    assert render(failed).startswith("🔴 <b>home</b>: provider <code>regru</code> failed")
    assert "<code>500</code>" in render(failed)
    assert render(back).startswith("🟢 <b>home</b>: provider <code>regru</code> recovered")


def test_retriever_status_failure_is_orange() -> None:
    event = parse_event(
        _event("retriever_status", '"retriever": "ifconfig", "success": false, "error": "slow"'),
    )

    assert isinstance(event, RetrieverStatus)
    assert render(event).startswith("🟠 <b>home</b>: retriever <code>ifconfig</code> failed")


def test_ip_change_groups_providers_with_the_same_change() -> None:
    changes = (
        '"changes": ['
        '{"provider": "regru", "family": "ipv4", "old": "1.2.3.4", "new": "5.6.7.8"},'
        '{"provider": "cloudflare", "family": "ipv4", "old": "1.2.3.4", "new": "5.6.7.8"},'
        '{"provider": "regru", "family": "ipv6", "old": "", "new": "2001:db8::1"}]'
    )

    event = parse_event(_event("ip_change", changes))
    text = render(event)

    assert isinstance(event, IpChange)
    assert text.startswith("🌐 <b>home</b> address changed")
    assert "ipv4: 1.2.3.4 → <code>5.6.7.8</code> (regru, cloudflare)" in text
    assert "ipv6: unknown → <code>2001:db8::1</code> (regru)" in text


def test_cycle() -> None:
    ok = parse_event(_event("cycle", '"success": true'))
    bad = parse_event(_event("cycle", '"success": false, "error": "boom"'))

    assert isinstance(ok, Cycle)
    assert render(ok).startswith("🔁 <b>home</b>: cycle finished")
    assert "cycle failed\n<code>boom</code>" in render(bad)


def test_lifecycle() -> None:
    started = parse_event(_event("lifecycle", '"state": "started", "version": "0.5.0"'))
    stopped = parse_event(_event("lifecycle", '"state": "stopped", "version": "0.5.0"'))

    assert isinstance(started, Lifecycle)
    assert render(started).startswith("▶️ <b>home</b> started (dnspatch 0.5.0)")
    assert render(stopped).startswith("⏹ <b>home</b> stopped")
