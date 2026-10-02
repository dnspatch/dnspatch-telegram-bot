from dnspatch_telegram_bot.events import parse_event, render
from tests.helpers import FAILED, RECOVERED, payload


def test_failure_escapes_html() -> None:
    text = render(parse_event(FAILED.replace("boom", "a<b")))

    assert text.startswith("🔴 <b>home</b>")
    assert "<code>a&lt;b</code>" in text
    assert "2026-10-01 05:00:00 UTC" in text


def test_recovery() -> None:
    assert render(parse_event(RECOVERED)).startswith("🟢 <b>home</b> is back to normal")


def test_status_of_a_newer_dnspatch() -> None:
    text = render(parse_event(payload("status", '"state": "recovery", "success": true')))

    assert text.startswith("🟢 <b>home</b> is back to normal")


def test_provider_status() -> None:
    failed = parse_event(
        payload("provider_status", '"provider": "regru", "success": false, "error": "500"'),
    )
    back = parse_event(payload("provider_status", '"provider": "regru", "success": true'))

    assert render(failed).startswith("🔴 <b>home</b>: provider <code>regru</code> failed")
    assert "<code>500</code>" in render(failed)
    assert render(back).startswith("🟢 <b>home</b>: provider <code>regru</code> recovered")


def test_retriever_failure_is_orange() -> None:
    event = parse_event(
        payload("retriever_status", '"retriever": "ifconfig", "success": false, "error": "slow"'),
    )

    assert render(event).startswith("🟠 <b>home</b>: retriever <code>ifconfig</code> failed")


def test_ip_change_groups_providers_with_the_same_change() -> None:
    changes = (
        '"changes": ['
        '{"provider": "regru", "family": "ipv4", "old": "1.2.3.4", "new": "5.6.7.8"},'
        '{"provider": "cloudflare", "family": "ipv4", "old": "1.2.3.4", "new": "5.6.7.8"},'
        '{"provider": "regru", "family": "ipv6", "old": "", "new": "2001:db8::1"}]'
    )

    text = render(parse_event(payload("ip_change", changes)))

    assert text.startswith("🌐 <b>home</b> address changed")
    assert "ipv4: 1.2.3.4 → <code>5.6.7.8</code> (regru, cloudflare)" in text
    assert "ipv6: unknown → <code>2001:db8::1</code> (regru)" in text


def test_cycle() -> None:
    ok = parse_event(payload("cycle", '"success": true'))
    bad = parse_event(payload("cycle", '"success": false, "error": "boom"'))

    assert render(ok).startswith("🔁 <b>home</b>: cycle finished")
    assert "cycle failed\n<code>boom</code>" in render(bad)


def test_lifecycle() -> None:
    started = parse_event(payload("lifecycle", '"state": "started", "version": "0.5.0"'))
    stopped = parse_event(payload("lifecycle", '"state": "stopped", "version": "0.5.0"'))

    assert render(started).startswith("▶️ <b>home</b> started (dnspatch 0.5.0)")
    assert render(stopped).startswith("⏹ <b>home</b> stopped")
