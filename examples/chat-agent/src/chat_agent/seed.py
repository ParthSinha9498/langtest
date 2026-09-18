import argparse
import json
import random
import uuid
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from chat_agent.graph import build_graph

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = PACKAGE_ROOT / "fixtures" / "checkpoints.db"
FORK_TARGET_FILENAME = "demo_fork_target.json"

FORK_DEMO_THREAD_ID = "fork-demo"
FORK_DEMO_MESSAGE = "add a random number to 50"

CHITCHAT_INPUTS = [
    "hey, how's it going?",
    "what's your favorite color?",
    "tell me a joke",
    "how are you today?",
    "what's the weather like where you are?",
]

CALCULATOR_INPUTS = [
    "add 12 and 30",
    "subtract 5 from 20",
    "multiply 6 and 7",
    "divide 100 by 4",
    "what is 47 plus 89?",
    "add a random number to 17",
]


def _run_turn(graph, thread_id: str, message: str) -> None:
    config = {"configurable": {"thread_id": thread_id}}
    graph.invoke({"messages": [HumanMessage(message)]}, config)


def _seed_random_threads(graph, num_threads: int, rng: random.Random) -> int:
    turns = 0
    for _ in range(num_threads):
        thread_id = str(uuid.uuid4())
        for _ in range(rng.randint(2, 3)):
            pool = CHITCHAT_INPUTS if rng.random() < 0.5 else CALCULATOR_INPUTS
            _run_turn(graph, thread_id, rng.choice(pool))
            turns += 1
    return turns


def _write_fork_demo_target(graph, fork_target_path: Path) -> dict:
    config = {"configurable": {"thread_id": FORK_DEMO_THREAD_ID}}
    fork_point = next(
        snapshot for snapshot in graph.get_state_history(config) if snapshot.next == ("tools",)
    )
    pending_call = fork_point.values["messages"][-1].tool_calls[0]
    target = {
        "thread_id": FORK_DEMO_THREAD_ID,
        "checkpoint_id": fork_point.config["configurable"]["checkpoint_id"],
        "pending_tool_call": pending_call["name"],
        "pending_tool_args": pending_call["args"],
        "description": (
            "Fork here, edit pending_tool_args, and replay to see the result diverge "
            "from the original thread — the canonical LangTest fork/replay demo."
        ),
    }
    fork_target_path.parent.mkdir(parents=True, exist_ok=True)
    fork_target_path.write_text(json.dumps(target, indent=2) + "\n")
    return target


def seed(db_path: Path, num_threads: int, seed_value: int, fresh: bool) -> None:
    if fresh and db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    fork_target_path = db_path.parent / FORK_TARGET_FILENAME

    rng = random.Random(seed_value)
    with SqliteSaver.from_conn_string(str(db_path)) as checkpointer:
        graph = build_graph(checkpointer)

        _run_turn(graph, FORK_DEMO_THREAD_ID, FORK_DEMO_MESSAGE)
        random_turns = _seed_random_threads(graph, num_threads, rng)
        fork_target = _write_fork_demo_target(graph, fork_target_path)

    print(f"Seeded {num_threads + 1} threads ({random_turns + 1} turns) into {db_path}")
    print(f"Fork demo target written to {fork_target_path}: {fork_target}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a LangTest example-app checkpoint database.")
    parser.add_argument("--num-threads", type=int, default=6, help="random threads beyond the fork demo one")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--seed", type=int, default=42, help="seeds which inputs are picked, not LLM output")
    parser.add_argument("--no-fresh", action="store_true", help="append to an existing db instead of resetting it")
    args = parser.parse_args()

    seed(args.db_path, args.num_threads, args.seed, fresh=not args.no_fresh)


if __name__ == "__main__":
    main()
