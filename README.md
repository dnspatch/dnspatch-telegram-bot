# dnspatch-telegram-bot

A Telegram bot that tells you when [dnspatch](https://github.com/dnspatch/dnspatch) fails to update a DNS record, and when it recovers.

dnspatch never talks to Telegram itself. With the `redis` notifier it publishes a small JSON event to the Redis channel `dnspatch.events.<instance>` whenever an instance flips between success and failure; this bot subscribes to those channels and forwards the events to your chats.

```
dnspatch ──PUBLISH──▶ Redis ──SUBSCRIBE──▶ bot ──▶ Telegram
```

## Quick start

You need Docker with Compose and a bot token from [@BotFather](https://t.me/BotFather). No sources to download, one file is enough:

```sh
curl -LO https://raw.githubusercontent.com/dnspatch/dnspatch-telegram-bot/main/compose.yaml
curl -L https://raw.githubusercontent.com/dnspatch/dnspatch-telegram-bot/main/.env.example -o .env
```

1. Put the token into `.env` as `TELEGRAM_TOKEN`, and the DNS account password as `PASSWORD`.
2. Edit the dnspatch config at the bottom of `compose.yaml` (the `configs:` section): replace the provider with yours. See the [dnspatch documentation](https://dnspatch.github.io/dnspatch/) for the providers and their parameters.
3. `docker compose up -d`.
4. Send `/start` to your bot. It replies with your chat id: put it into `.env` as `TELEGRAM_CHAT_IDS` and run `docker compose up -d` again.

The notifiers are compiled into the `-full` image of dnspatch only, which is what `compose.yaml` runs.

## Commands

| Command | Who | What it does |
|---------|-----|--------------|
| `/start` | anyone | Replies with the chat id, to put into `TELEGRAM_CHAT_IDS`. |
| `/status` | chats from `TELEGRAM_CHAT_IDS` | Shows the last known status of every instance. |

## Configuration

The bot is configured with environment variables.

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_TOKEN` | required | Token of the bot. |
| `TELEGRAM_CHAT_IDS` | empty | Comma separated chat ids that receive notifications and may use `/status`. With none, the bot only answers `/start`. |
| `REDIS_URL` | `redis://redis:6379/0` | A `redis://` or `rediss://` URL. |
| `TOPIC_PREFIX` | `dnspatch.events.` | Must match `topic_prefix` of the dnspatch notifier. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR`. |

## Good to know

- Redis Pub/Sub does not queue anything: an event published while the bot is down or reconnecting is lost. The next status change is announced as usual, and dnspatch's own health check and `ping_url` cover "the daemon is stuck".
- The bot keeps the last event of every instance in the Redis key `dnspatch-telegram-bot:status` for `/status`; the compose file stores it in a volume.
- Messages that are not dnspatch events are logged and ignored.

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
