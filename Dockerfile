# One image for the whole Python uv workspace (sdk, server, examples/chat-agent).
# They're workspace members with cross-package imports (see
# server/src/langtest_server/example_app.py), so splitting them into separate
# images would mean duplicating the workspace into each one anyway — a single
# image with different `command:` overrides per service (see
# docker-compose.yml) is simpler and keeps one dependency set to install.
FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /workspace

COPY pyproject.toml uv.lock ./
COPY sdk/pyproject.toml sdk/pyproject.toml
COPY server/pyproject.toml server/pyproject.toml
COPY examples/chat-agent/pyproject.toml examples/chat-agent/pyproject.toml

# Install dependencies first, in their own layer, so editing application code
# doesn't invalidate the (slow) dependency-resolution cache.
RUN uv sync --no-install-workspace

COPY sdk sdk
COPY server server
COPY examples/chat-agent examples/chat-agent

RUN uv sync

ENV PATH="/workspace/.venv/bin:${PATH}"

EXPOSE 8010

CMD ["python", "-m", "uvicorn", "langtest_server.app:app", "--host", "0.0.0.0", "--port", "8010"]
