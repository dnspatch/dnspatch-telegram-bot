FROM python:3.14-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

# Bytecode is compiled once at build time, so the container starts faster; the
# interpreter of the image is the one the environment is built for.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first: this layer is rebuilt only when the lock file changes.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable


FROM python:3.14-slim

COPY --from=build /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# An unprivileged user, the same uid as the dnspatch image uses.
USER 65532:65532

ENTRYPOINT ["dnspatch-telegram-bot"]
