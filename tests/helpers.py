"""Payloads of dnspatch and fakes of Telegram, shared by the tests."""

from unittest.mock import AsyncMock, MagicMock

TIME = '"time": "2026-10-01T05:00:00Z"'

# What 0.4.0 published: no "event", only the status.
FAILED = '{"instance": "home", "success": false, "error": "boom", ' + TIME + "}"
RECOVERED = '{"instance": "home", "success": true, "time": "2026-10-01T05:05:00Z"}'
OFFICE = '{"instance": "office", "success": true, ' + TIME + "}"


def payload(event: str, body: str) -> str:
    """Build the payload of a typed event of the instance ``home``."""
    return f'{{"event": "{event}", "severity": "info", "instance": "home", {body}, {TIME}}}'


CYCLE = payload("cycle", '"success": true')
REGRU_DOWN = payload(
    "provider_status",
    '"provider": "regru", "success": false, "error": "boom"',
)
CLOUDFLARE_DOWN = REGRU_DOWN.replace("regru", "cloudflare")


def message(chat_id: int) -> MagicMock:
    """Build a Telegram message from a chat; ``answer`` records the replies."""
    msg = MagicMock()
    msg.chat.id = chat_id
    msg.answer = AsyncMock()
    return msg


def answer(msg: MagicMock) -> str:
    """Return the text of the last reply to a message."""
    text = msg.answer.await_args.args[0]
    assert isinstance(text, str)
    return text
