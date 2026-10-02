# dnspatch-telegram-bot

A Telegram bot that tells you what [dnspatch](https://github.com/dnspatch/dnspatch) does: when it fails to update a DNS record and when it recovers, when your address changes, when it starts or stops.

dnspatch never talks to Telegram itself. With the `redis` notifier it publishes small JSON events to the Redis channel `dnspatch.events.<instance>`; this bot subscribes to those channels and forwards the events to your chats. It understands every [event type](https://dnspatch.github.io/dnspatch/operations/notification-events/) of dnspatch:

| Event | In the chat |
|-------|-------------|
| `status` | 🔴 the instance failed to update / 🟢 is back to normal |
| `provider_status` | 🔴 one provider failed / 🟢 recovered |
| `retriever_status` | 🟠 one retriever failed / 🟢 recovered |
| `ip_change` | 🌐 the address changed, `old → new` per family and provider |
| `cycle` | 🔁 a cycle finished or failed (not sent by default, see `EVENTS`) |
| `lifecycle` | ▶️ an instance started / ⏹ stopped |

```
dnspatch ──PUBLISH──▶ Redis ──SUBSCRIBE──▶ bot ──▶ Telegram
```

## Quick start

You need Docker with Compose and a bot token from [@BotFather](https://t.me/BotFather). No sources to download, three small files are enough:

```sh
curl -LO https://raw.githubusercontent.com/dnspatch/dnspatch-telegram-bot/main/compose.yaml
curl -L https://raw.githubusercontent.com/dnspatch/dnspatch-telegram-bot/main/.env.example -o .env
curl -L https://raw.githubusercontent.com/dnspatch/dnspatch-telegram-bot/main/dnspatch.toml.example -o dnspatch.toml
```

1. Put the token into `.env` as `TELEGRAM_TOKEN`, and the DNS account password as `PASSWORD`.
2. Edit the dnspatch config `dnspatch.toml` next to `compose.yaml`: replace the provider with yours. See the [dnspatch documentation](https://dnspatch.github.io/dnspatch/) for the providers and their parameters.
3. `docker compose up -d`.
4. Send `/subscribe` to your bot: this chat now gets the notifications. That is all for a bot of your own; to restrict it to certain chats, see `TELEGRAM_CHAT_IDS` below.

The notifiers are compiled into the `-full` image of dnspatch only, which is what `compose.yaml` runs (`latest-full`). The event types need dnspatch 0.4.1 or newer; 0.4.0 publishes `status` only, which the bot still understands.

Which events dnspatch publishes is set by `events` of the notifier in its config, as in `dnspatch.toml.example`; which of them reach the chat is set by `EVENTS` of the bot.

## Commands

| Command | Who | What it does |
|---------|-----|--------------|
| `/start` | anyone | Replies with the chat id, to put into `TELEGRAM_CHAT_IDS`. |
| `/subscribe` | anyone, while `TELEGRAM_CHAT_IDS` is empty | Subscribes the chat to the notifications. |
| `/unsubscribe` | subscribed chats | Cancels the subscription. |
| `/status` | chats that get the notifications | Shows the latest event of every kind for every instance, provider and retriever, whether or not it was sent to the chat. |

## Configuration

The bot is configured with environment variables.

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_TOKEN` | required | Token of the bot. |
| `TELEGRAM_CHAT_IDS` | empty | Comma separated chat ids that receive notifications and may use `/status`. With none, any chat can subscribe itself with `/subscribe`. With some, they are the only ones: `/subscribe` is ignored from other chats, and chats that subscribed earlier stop getting notifications. |
| `REDIS_URL` | `redis://redis:6379/0` | A `redis://` or `rediss://` URL. |
| `TOPIC_PREFIX` | `dnspatch.events.` | Must match `topic_prefix` of the dnspatch notifier. |
| `EVENTS` | all but `cycle` | Comma separated event types that are sent to the chats. Every event is kept for `/status` either way. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR`. |

## Good to know

- Anyone who finds the bot can `/subscribe` while `TELEGRAM_CHAT_IDS` is empty, and then sees your addresses and errors. That is fine for a bot nobody knows about; otherwise send `/start` from your chat, put the id it shows into `TELEGRAM_CHAT_IDS` and restart.
- Subscribers are kept in the Redis set `dnspatch-telegram-bot:chats`, in the same volume as the events.
- Redis Pub/Sub does not queue anything: an event published while the bot is down or reconnecting is lost. The next status change is announced as usual, and dnspatch's own health check and `ping_url` cover "the daemon is stuck".
- The bot keeps the latest event of every kind in the Redis hash `dnspatch-telegram-bot:events` for `/status`; the compose file stores it in a volume. Version 0.1 used `dnspatch-telegram-bot:status`, which is no longer read and can be deleted.
- dnspatch sends the `ip_change` of every provider again after each restart, with an unknown old address: that is dnspatch remembering nothing between runs, not an address change.
- Messages that are not dnspatch events, and event types this bot does not know, are logged and ignored.

## Development

Python 3.13 and [uv](https://docs.astral.sh/uv/):

```sh
uv sync
uv run ruff format --check && uv run ruff check   # every ruff rule is enabled
uv run ty check                                   # every ty rule is an error
uv run pytest
```

To build the image from a checkout instead of pulling it, run `docker build -t dnspatch-telegram-bot .`, or `docker compose up -d --build` after adding `build: .` to the `bot` service.

## License

MIT
