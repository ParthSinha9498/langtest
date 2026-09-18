from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from chat_agent.llm import get_calculator_model, get_chitchat_model
from chat_agent.router import classify
from chat_agent.state import ChatState
from chat_agent.tools import TOOLS

CALCULATOR_SYSTEM_PROMPT = SystemMessage(
    "You are a calculator agent. For any arithmetic, you MUST call the matching "
    "tool (add, subtract, multiply, divide) — never compute the result yourself, "
    "even for simple numbers. Only call add_random_number if the user explicitly "
    "asks for randomness (e.g. 'add a random number to X'); never use it for a "
    "plain addition. Once the tool has responded, report its result."
)


def build_graph(checkpointer):
    # Constructed lazily, on first actual use, rather than here: callers that
    # only need the graph's structure (e.g. get_state_history()/get_graph(),
    # never invoke()) shouldn't pay for building an LLM client they'll never use.
    chitchat_model = None
    calculator_model = None

    def router_node(state: ChatState) -> dict:
        return {}

    def route_after_router(state: ChatState) -> str:
        return classify(state["messages"][-1].content)

    def chitchat_node(state: ChatState) -> dict:
        nonlocal chitchat_model
        if chitchat_model is None:
            chitchat_model = get_chitchat_model()
        return {"messages": [chitchat_model.invoke(state["messages"])]}

    def calculator_agent_node(state: ChatState) -> dict:
        nonlocal calculator_model
        if calculator_model is None:
            calculator_model = get_calculator_model().bind_tools(TOOLS)
        response = calculator_model.invoke([CALCULATOR_SYSTEM_PROMPT, *state["messages"]])
        return {"messages": [response]}

    def route_after_calculator(state: ChatState) -> str:
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    builder = StateGraph(ChatState)
    builder.add_node("router", router_node)
    builder.add_node("chitchat", chitchat_node)
    builder.add_node("calculator_agent", calculator_agent_node)
    builder.add_node("tools", ToolNode(TOOLS))

    builder.add_edge(START, "router")
    builder.add_conditional_edges(
        "router", route_after_router, {"chitchat": "chitchat", "calculator": "calculator_agent"}
    )
    builder.add_edge("chitchat", END)
    builder.add_conditional_edges("calculator_agent", route_after_calculator, {"tools": "tools", END: END})
    builder.add_edge("tools", "calculator_agent")

    return builder.compile(checkpointer=checkpointer)
