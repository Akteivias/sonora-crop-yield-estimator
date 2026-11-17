FROM python:3.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.10.11 /uv /uvx /bin/

ENV PATH="/app/.venv/bin:$PATH" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY data/ ./data/
COPY data_manifest.json train.py predict.py ./
RUN python train.py

RUN useradd --create-home --no-log-init appuser

USER appuser
EXPOSE 10000
CMD ["sh", "-c", "exec uvicorn predict:app --host 0.0.0.0 --port ${PORT:-9696}"]
