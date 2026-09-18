from langchain_core.tools import tool

RANDOM_NUMBER_OFFSET = 3


@tool
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@tool
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


@tool
def divide(a: float, b: float) -> float:
    """Divide a by b."""
    return a / b


@tool
def add_random_number(a: float) -> float:
    """Add a fixed offset to a. Only call this when the user explicitly asks for
    randomness — deterministic (not actually random) so that changing
    RANDOM_NUMBER_OFFSET and re-running is a repeatable way to test the
    fork/replay flow: fork right before this executes, edit its argument,
    replay, and the result changes exactly as expected.
    """
    return a + RANDOM_NUMBER_OFFSET


TOOLS = [add, subtract, multiply, divide, add_random_number]
