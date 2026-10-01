"""The event dnspatch publishes and how it looks in a chat."""

from datetime import datetime
from html import escape

from pydantic import BaseModel, ConfigDict


class Event(BaseModel):
    """A status flip of one instance: {"instance", "success", "error", "time"}."""

    model_config = ConfigDict(frozen=True)

    instance: str
    success: bool
    error: str = ""
    time: datetime


def parse_event(payload: str | bytes) -> Event:
    """Decode a published payload; raises pydantic.ValidationError when it is not an event."""
    return Event.model_validate_json(payload)


def render(event: Event) -> str:
    """Format an event as an HTML message for Telegram."""
    name = f"<b>{escape(event.instance)}</b>"
    stamp = event.time.strftime("%Y-%m-%d %H:%M:%S %Z").strip()

    if event.success:
        return f"🟢 {name} is back to normal\n<i>{escape(stamp)}</i>"

    reason = f"\n<code>{escape(event.error)}</code>" if event.error else ""
    return f"🔴 {name} failed to update{reason}\n<i>{escape(stamp)}</i>"
