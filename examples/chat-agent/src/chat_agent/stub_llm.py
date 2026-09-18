import re
from typing import Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool

_NUM = r"-?\d+(?:\.\d+)?"

_RANDOM_PATTERNS = [
    re.compile(rf"add\s+a\s+random\s+number\s+to\s+({_NUM})", re.IGNORECASE),
    re.compile(rf"add\s+({_NUM})\s+and\s+a\s+random\s+number", re.IGNORECASE),
    re.compile(rf"randomi[sz]e\s+({_NUM})", re.IGNORECASE),
]

_PATTERNS = [
    (re.compile(rf"add\s+({_NUM})\s+and\s+({_NUM})", re.IGNORECASE), "add"),
    (re.compile(rf"({_NUM})\s+plus\s+({_NUM})", re.IGNORECASE), "add"),
    (re.compile(rf"({_NUM})\s*\+\s*({_NUM})"), "add"),
    (re.compile(rf"subtract\s+({_NUM})\s+from\s+({_NUM})", re.IGNORECASE), "subtract_reversed"),
    (re.compile(rf"({_NUM})\s*-\s*({_NUM})"), "subtract"),
    (re.compile(rf"multiply\s+({_NUM})\s+(?:by|and)\s+({_NUM})", re.IGNORECASE), "multiply"),
    (re.compile(rf"({_NUM})\s*\*\s*({_NUM})"), "multiply"),
    (re.compile(rf"divide\s+({_NUM})\s+by\s+({_NUM})", re.IGNORECASE), "divide"),
    (re.compile(rf"({_NUM})\s*/\s*({_NUM})"), "divide"),
]


def _last_human_text(messages: Sequence[BaseMessage]) -> str:
    last_human = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    return last_human.content if last_human else ""


class StubChitchatModel:
    """Deterministic stand-in for the Groq chitchat model, used until GROQ_API_KEY is configured."""

    def invoke(self, messages: Sequence[BaseMessage]) -> AIMessage:
        text = _last_human_text(messages)
        return AIMessage(content=f"(stub chitchat reply) you said: {text}")

    async def ainvoke(self, messages: Sequence[BaseMessage]) -> AIMessage:
        return self.invoke(messages)


class StubCalculatorModel:
    """Deterministic stand-in for the Groq tool-calling model driving the calculator ReAct loop."""

    def __init__(self) -> None:
        self._tools: list[BaseTool] = []

    def bind_tools(self, tools: Sequence[BaseTool]) -> "StubCalculatorModel":
        self._tools = list(tools)
        return self

    def invoke(self, messages: Sequence[BaseMessage]) -> AIMessage:
        if isinstance(messages[-1], ToolMessage):
            return self._final_answer(messages)
        return self._first_tool_call(messages)

    async def ainvoke(self, messages: Sequence[BaseMessage]) -> AIMessage:
        return self.invoke(messages)

    def _first_tool_call(self, messages: Sequence[BaseMessage]) -> AIMessage:
        text = _last_human_text(messages)
        for random_pattern in _RANDOM_PATTERNS:
            match = random_pattern.search(text)
            if match:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "add_random_number",
                            "args": {"a": float(match.group(1))},
                            "id": "stub-call-1",
                            "type": "tool_call",
                        }
                    ],
                )
        for pattern, name in _PATTERNS:
            match = pattern.search(text)
            if not match:
                continue
            a, b = float(match.group(1)), float(match.group(2))
            if name == "subtract_reversed":
                name, a, b = "subtract", b, a
            return AIMessage(
                content="",
                tool_calls=[{"name": name, "args": {"a": a, "b": b}, "id": "stub-call-1", "type": "tool_call"}],
            )
        return AIMessage(content="(stub calculator reply) I couldn't parse a calculation out of that.")

    def _final_answer(self, messages: Sequence[BaseMessage]) -> AIMessage:
        result = next(m.content for m in reversed(messages) if isinstance(m, ToolMessage))
        return AIMessage(content=f"(stub calculator reply) result: {result}")
