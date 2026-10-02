from dnspatch_telegram_bot.bot.handlers.start import start
from tests.helpers import answer, message


async def test_tells_the_chat_id() -> None:
    msg = message(42)

    await start(msg, configured_chats=frozenset({1}))

    assert "<code>42</code>" in answer(msg)
    assert "/subscribe" not in answer(msg)


async def test_offers_to_subscribe_when_open() -> None:
    msg = message(42)

    await start(msg, configured_chats=frozenset())

    assert "/subscribe" in answer(msg)
