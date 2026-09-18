import sys

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from chat_agent.graph import build_graph

DEFAULT_DB_PATH = "checkpoints.db"


def run_turn(db_path: str, thread_id: str, message: str) -> str:
    with SqliteSaver.from_conn_string(db_path) as checkpointer:
        graph = build_graph(checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        result = graph.invoke({"messages": [HumanMessage(message)]}, config)
        return result["messages"][-1].content


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: python -m chat_agent.run <thread_id> <message> [db_path]")
        raise SystemExit(1)
    thread_id, message = sys.argv[1], sys.argv[2]
    db_path = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_DB_PATH
    print(run_turn(db_path, thread_id, message))


if __name__ == "__main__":
    main()
