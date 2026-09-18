from fastapi import APIRouter
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel

from langtest_server.example_app import build_graph

router = APIRouter()


class GraphTopology(BaseModel):
    mermaid: str


@router.get("/graph", response_model=GraphTopology)
def get_graph_topology() -> GraphTopology:
    graph = build_graph(InMemorySaver())
    return GraphTopology(mermaid=graph.get_graph().draw_mermaid())
