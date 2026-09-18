# LangTest

Time-travel debugging for [LangGraph](https://github.com/langchain-ai/langgraph) apps — an open-source alternative to LangSmith's tracing UI, with **fork-and-replay** as the core feature: pick any point in a run, edit the state, and resume from there to see how the outcome changes, without touching the original run.

Wrap your already-compiled graph with one function call. LangTest reads the checkpointer you already attached — it never provisions storage of its own — and gives you a UI to browse every thread's checkpoint history, visualize which nodes ran, and fork from any checkpoint.

## Quickstart

```python
from langtest import langtest

graph = builder.compile(checkpointer=SqliteSaver.from_conn_string("checkpoints.db"))
graph = langtest(graph, port=8010)  # starts the LangTest server, returns a transparent wrapper

result = graph.invoke(...)       # behaves exactly like the unwrapped graph
result = await graph.ainvoke(...)
```

Open `http://localhost:8010` (or run the frontend — see below) to browse threads, inspect state at each step, and fork.

## Repo layout

```
langtest/
├── sdk/                    # langtest() — wraps a compiled graph, starts the server
├── server/                 # FastAPI backend: reads/writes the graph's checkpointer
├── frontend/                # React + TypeScript UI: topology, history, fork editor
├── examples/chat-agent/     # sample LangGraph app (router → chitchat / calculator) used to exercise it
├── docker-compose.yml
└── Makefile
```

## How it works

- **SDK** (`sdk/`) — `langtest(graph, port=8010)` wraps an already-compiled graph. It reads the sqlite path off the checkpointer you compiled with and starts the server pointed at it, as a separate subprocess. No restructuring of your code required, and no checkpointer is provisioned for you — bring your own.
- **Server** (`server/`) — a FastAPI app that reads and writes the checkpointer's storage directly:
  - `GET /threads` — every thread in the database.
  - `GET /threads/{id}/history` — full checkpoint history for a thread, including which node produced each step and what's pending next.
  - `GET /graph` — the graph's topology as Mermaid, straight from LangGraph's own `get_graph().draw_mermaid()`.
  - `POST /fork` — given a thread, a checkpoint, and edited state values, creates a **new thread** starting from that point with the edit applied. The original thread's history is never touched. Only state *values* are editable — not routing.
- **Frontend** (`frontend/`) — browse threads, see the topology with visited/pending nodes highlighted, inspect state at any checkpoint, edit it as JSON, and fork.
- **Example app** (`examples/chat-agent/`) — a small router-based agent (chitchat vs. a calculator ReAct loop with `add`/`subtract`/`multiply`/`divide`/`add_random_number` tools) used to build and test against. Runs against a real Groq model if `GROQ_API_KEY` is set, otherwise falls back to a deterministic stub so the whole stack is testable without a network call.

## Running it

```bash
make setup         # install all Python deps (uv workspace: sdk, server, example app)
make run-example    # seed a sqlite db with example conversations
make server         # start the FastAPI server against that db
make frontend       # start the frontend dev server (via Docker, no local Node needed)
```

Drop a Groq API key into `.env` (see `.env.example`) to run the example app against a real model instead of its deterministic stub.

### Tests

```bash
make test
```

### Docker

```bash
make docker-build
make docker-up                       # server + frontend
docker compose run --rm chat-agent   # seed the database (one-off)
```

Checkpoint data persists in a named Docker volume across container restarts.
