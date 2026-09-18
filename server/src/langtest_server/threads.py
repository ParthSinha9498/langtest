import copy
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from langchain_core.messages import BaseMessage
from langchain_core.messages.utils import convert_to_messages
from langgraph.checkpoint.base.id import uuid6
from pydantic import BaseModel

from langtest_server.checkpointer import open_checkpointer
from langtest_server.example_app import build_graph

router = APIRouter()


class ThreadSummary(BaseModel):
    thread_id: str
    checkpoint_count: int
    latest_checkpoint_id: str
    updated_at: str


class CheckpointSnapshot(BaseModel):
    checkpoint_id: str
    parent_checkpoint_id: str | None
    step: int
    created_at: str
    source: str
    values: dict[str, Any]
    next: list[str]
    produced_by_nodes: list[str]


class ForkRequest(BaseModel):
    thread_id: str
    checkpoint_id: str
    edited_state: dict[str, Any]


class ForkResponse(BaseModel):
    thread_id: str


@router.get("/threads", response_model=list[ThreadSummary])
def list_threads() -> list[ThreadSummary]:
    with open_checkpointer() as saver:
        by_thread: dict[str, list[Any]] = {}
        for tup in saver.list(None):
            thread_id = tup.config["configurable"]["thread_id"]
            by_thread.setdefault(thread_id, []).append(tup)

    summaries = []
    for thread_id, tuples in by_thread.items():
        latest = max(tuples, key=lambda t: t.checkpoint["id"])
        summaries.append(
            ThreadSummary(
                thread_id=thread_id,
                checkpoint_count=len(tuples),
                latest_checkpoint_id=latest.checkpoint["id"],
                updated_at=latest.checkpoint["ts"],
            )
        )
    return sorted(summaries, key=lambda s: s.updated_at, reverse=True)


@router.get("/threads/{thread_id}/history", response_model=list[CheckpointSnapshot])
def get_thread_history(thread_id: str) -> list[CheckpointSnapshot]:
    with open_checkpointer() as saver:
        graph = build_graph(saver)
        history = list(graph.get_state_history({"configurable": {"thread_id": thread_id}}))

    if not history:
        raise HTTPException(status_code=404, detail=f"No such thread: {thread_id}")

    # `next` on a snapshot names the node(s) about to run *from* it — so the
    # node(s) that produced the checkpoint at step k are whatever the
    # step-(k-1) snapshot's `next` said was coming (more than one for a
    # parallel fan-out: they land in a single checkpoint together). There is
    # no such parent for step 0 (the graph's own entry point, "__start__",
    # produced it instead).
    by_step = {snap.metadata.get("step", 0): snap for snap in history}

    snapshots = [_to_checkpoint_snapshot(snap, by_step) for snap in history]
    return sorted(snapshots, key=lambda s: s.step)


def _to_checkpoint_snapshot(snap: Any, by_step: dict[int, Any]) -> CheckpointSnapshot:
    step = snap.metadata.get("step", 0)
    parent = by_step.get(step - 1)
    return CheckpointSnapshot(
        checkpoint_id=snap.config["configurable"]["checkpoint_id"],
        parent_checkpoint_id=snap.parent_config["configurable"]["checkpoint_id"] if snap.parent_config else None,
        step=step,
        created_at=snap.created_at,
        source=snap.metadata.get("source", "unknown"),
        values=snap.values,
        next=list(snap.next),
        produced_by_nodes=list(parent.next) if parent else [],
    )


def _coerce_edited_value(original_value: Any, edited_value: Any) -> Any:
    """Re-hydrate a JSON-submitted replacement for a message-list channel.

    The frontend edits state as plain JSON, so a replacement for a
    `messages`-shaped channel arrives as a list of plain dicts, not
    HumanMessage/AIMessage instances. If the channel's existing value was a
    list of BaseMessage, convert the edited list back into real message
    objects via LangChain's own coercion — otherwise a resumed run would see
    dicts instead of messages and node code (e.g. `msg.tool_calls`) would break.

    The existing value being empty (or the channel not existing yet, e.g. the
    very first checkpoint) isn't proof it's *not* a message channel, so it's
    not enough to skip coercion — only a *non-empty* list confirmed to hold
    something else should skip it. Otherwise, attempt the conversion and fall
    back to the raw value if it doesn't look like messages after all.
    """
    if not isinstance(edited_value, list):
        return edited_value
    if isinstance(original_value, list) and original_value and not isinstance(original_value[0], BaseMessage):
        return edited_value
    try:
        return convert_to_messages(edited_value)
    except Exception:
        return edited_value


@router.post("/fork", response_model=ForkResponse, status_code=201)
def fork_thread(request: ForkRequest) -> ForkResponse:
    with open_checkpointer() as saver:
        source_config = {
            "configurable": {
                "thread_id": request.thread_id,
                "checkpoint_id": request.checkpoint_id,
            }
        }
        source = saver.get_tuple(source_config)
        if source is None:
            raise HTTPException(
                status_code=404,
                detail=f"No checkpoint {request.checkpoint_id} on thread {request.thread_id}",
            )

        new_checkpoint = copy.deepcopy(source.checkpoint)
        new_checkpoint["id"] = str(uuid6())
        new_checkpoint["ts"] = datetime.now(timezone.utc).isoformat()
        for key, edited_value in copy.deepcopy(request.edited_state).items():
            original_value = source.checkpoint["channel_values"].get(key)
            new_checkpoint["channel_values"][key] = _coerce_edited_value(original_value, edited_value)

        new_thread_id = str(uuid.uuid4())
        new_config = {"configurable": {"thread_id": new_thread_id, "checkpoint_ns": ""}}
        new_metadata = {
            "source": "fork",
            "step": source.metadata.get("step", 0),
            "parents": {},
        }
        saver.put(new_config, new_checkpoint, new_metadata, {})

    return ForkResponse(thread_id=new_thread_id)
