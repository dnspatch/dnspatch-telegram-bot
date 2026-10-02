"""The events dnspatch publishes and how they look in a chat."""

from datetime import datetime
from html import escape
from typing import Annotated, Literal, override

from pydantic import BaseModel, ConfigDict, Discriminator, Tag, TypeAdapter

# In the order /status lists them.
KINDS = ("status", "provider_status", "retriever_status", "ip_change", "cycle", "lifecycle")


class _Event(BaseModel):
    """The fields every event has; ``severity`` is ignored, the text says it all."""

    model_config = ConfigDict(frozen=True)

    event: str
    instance: str
    time: datetime

    @property
    def key(self) -> str:
        """Identify what this event is the latest word about."""
        return f"{self.instance}:{self.event}"


class Status(_Event):
    """The instance as a whole flipped between success and failure.

    0.4.0 published only this one, without the ``event`` field.
    """

    event: Literal["status"] = "status"
    success: bool
    error: str = ""


class ProviderStatus(_Event):
    """One provider flipped between success and failure."""

    event: Literal["provider_status"] = "provider_status"
    provider: str
    success: bool
    error: str = ""

    @property
    @override
    def key(self) -> str:
        """Identify the provider within the instance."""
        return f"{super().key}:{self.provider}"


class RetrieverStatus(_Event):
    """One retriever flipped between success and failure."""

    event: Literal["retriever_status"] = "retriever_status"
    retriever: str
    success: bool
    error: str = ""

    @property
    @override
    def key(self) -> str:
        """Identify the retriever within the instance."""
        return f"{super().key}:{self.retriever}"


class Change(BaseModel):
    """One address written to one provider; ``old`` is empty when it is not known."""

    model_config = ConfigDict(frozen=True)

    provider: str
    family: str
    old: str = ""
    new: str


class IpChange(_Event):
    """Addresses were written to providers, once per cycle."""

    event: Literal["ip_change"] = "ip_change"
    changes: tuple[Change, ...]


class Cycle(_Event):
    """A cycle finished."""

    event: Literal["cycle"] = "cycle"
    success: bool
    error: str = ""


class Lifecycle(_Event):
    """An instance started or stopped."""

    event: Literal["lifecycle"] = "lifecycle"
    state: Literal["started", "stopped"]
    version: str = ""


def _kind(raw: object) -> str | None:
    """Pick the model of a payload; an unknown type is left to fail validation."""
    kind = raw.get("event", "status") if isinstance(raw, dict) else getattr(raw, "event", None)
    return kind if isinstance(kind, str) else None


type Event = Annotated[
    Annotated[Status, Tag("status")]
    | Annotated[ProviderStatus, Tag("provider_status")]
    | Annotated[RetrieverStatus, Tag("retriever_status")]
    | Annotated[IpChange, Tag("ip_change")]
    | Annotated[Cycle, Tag("cycle")]
    | Annotated[Lifecycle, Tag("lifecycle")],
    Discriminator(_kind),
]

_ADAPTER: TypeAdapter[Event] = TypeAdapter(Event)


def parse_event(payload: str | bytes) -> Event:
    """Decode a published payload; raises pydantic.ValidationError when it is not an event."""
    return _ADAPTER.validate_json(payload)


def render(event: Event) -> str:
    """Format an event as an HTML message for Telegram."""
    stamp = event.time.strftime("%Y-%m-%d %H:%M:%S %Z").strip()
    return f"{_headline(event)}\n<i>{escape(stamp)}</i>"


def _headline(event: Event) -> str:
    name = f"<b>{escape(event.instance)}</b>"

    match event:
        case IpChange():
            return f"🌐 {name} address changed\n{_changes(event.changes)}"
        case Lifecycle(state="started"):
            version = f" (dnspatch {escape(event.version)})" if event.version else ""
            return f"▶️ {name} started{version}"
        case Lifecycle():
            return f"⏹ {name} stopped"
        case _:
            return _outcome(name, event)


def _outcome(name: str, event: Status | ProviderStatus | RetrieverStatus | Cycle) -> str:
    """Describe an event that says whether something worked."""
    match event:
        case Status():
            subject, worked, failed = name, "is back to normal", "failed to update"
            icons = ("🟢", "🔴")
        case ProviderStatus():
            subject = f"{name}: provider <code>{escape(event.provider)}</code>"
            worked, failed, icons = "recovered", "failed", ("🟢", "🔴")
        case RetrieverStatus():
            subject = f"{name}: retriever <code>{escape(event.retriever)}</code>"
            # A fallback retriever may still serve the cycle, so it is not red.
            worked, failed, icons = "recovered", "failed", ("🟢", "🟠")
        case Cycle():
            subject, worked, failed = f"{name}: cycle", "finished", "failed"
            icons = ("🔁", "🔁")

    if event.success:
        return f"{icons[0]} {subject} {worked}"
    return f"{icons[1]} {subject} {failed}{_reason(event.error)}"


def _reason(error: str) -> str:
    return f"\n<code>{escape(error)}</code>" if error else ""


def _changes(changes: tuple[Change, ...]) -> str:
    """List the changes, one line per distinct old/new pair of a family."""
    providers: dict[tuple[str, str, str], list[str]] = {}
    for change in changes:
        providers.setdefault((change.family, change.old, change.new), []).append(change.provider)

    return "\n".join(
        f"{escape(family)}: {escape(old) or 'unknown'} → <code>{escape(new)}</code>"
        f" ({escape(', '.join(names))})"
        for (family, old, new), names in providers.items()
    )
