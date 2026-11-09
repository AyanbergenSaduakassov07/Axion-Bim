FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.6.5 /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV AXIOM_DATA_DIR="/data"

VOLUME ["/data"]
EXPOSE 8000

CMD ["axiom", "serve", "--host", "0.0.0.0", "--port", "8000"]
