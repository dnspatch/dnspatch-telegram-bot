"""How an event looks in a chat."""

from html import escape

from dnspatch_telegram_bot.events.models import (
    Change,
    Cycle,
    Event,
    IpChange,
    Lifecycle,
    ProviderStatus,
    RetrieverStatus,
    Status,
)


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
