"""The events dnspatch publishes."""

from datetime import datetime
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
