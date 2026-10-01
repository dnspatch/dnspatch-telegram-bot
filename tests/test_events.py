import pytest
from pydantic import ValidationError

from dnspatch_telegram_bot.events import parse_event, render

FAILED = '{"instance": "home", "success": false, "error": "a<b", "time": "2026-10-01T05:00:00Z"}'
RECOVERED = '{"instance": "home", "success": true, "time": "2026-10-01T05:05:00Z"}'


def test_render_failure_escapes_html() -> None:
    text = render(parse_event(FAILED))

    assert text.startswith("🔴 <b>home</b>")
    assert "<code>a&lt;b</code>" in text
    assert "2026-10-01 05:00:00 UTC" in text


def test_render_recovery() -> None:
    assert render(parse_event(RECOVERED)).startswith("🟢 <b>home</b> is back to normal")


def test_parse_accepts_bytes() -> None:
    assert parse_event(RECOVERED.encode()).success


def test_parse_rejects_garbage() -> None:
    with pytest.raises(ValidationError):
        parse_event("not json")
