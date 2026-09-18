.PHONY: setup test run-example server frontend docker-build docker-up docker-down

LANGTEST_DB_PATH ?= $(CURDIR)/examples/chat-agent/fixtures/checkpoints.db
LANGTEST_PORT ?= 8010
FRONTEND_PORT ?= 5173

setup:
	uv sync

test:
	uv run pytest sdk/tests server/tests examples/chat-agent/tests -v

run-example:
	uv run --project examples/chat-agent python -m chat_agent.seed

# Runs the FastAPI server directly against LANGTEST_DB_PATH (defaults to the
# fixture db from `make run-example`). This is the same server the SDK starts
# for you automatically when langtest(graph) is called in your own app — this
# target is for running it standalone, e.g. against the example app's data.
server:
	LANGTEST_DB_PATH=$(LANGTEST_DB_PATH) LANGTEST_PORT=$(LANGTEST_PORT) \
		uv run python -m uvicorn langtest_server.app:app --host 0.0.0.0 --port $(LANGTEST_PORT)

# No Node.js required on the host: runs the Vite dev server (hot reload) in a
# container against the bind-mounted source, as a non-root user so files it
# writes (node_modules, lockfile) stay owned by you, not root.
frontend:
	docker run --rm -it \
		--user "$$(id -u):$$(id -g)" -e HOME=/tmp \
		-e VITE_API_BASE_URL=http://localhost:$(LANGTEST_PORT) \
		-v "$(CURDIR)/frontend":/app -w /app \
		-p $(FRONTEND_PORT):5173 \
		node:20-alpine sh -c "npm install && npm run dev -- --host 0.0.0.0"

docker-build:
	docker compose build

docker-up:
	docker compose up

docker-down:
	docker compose down
