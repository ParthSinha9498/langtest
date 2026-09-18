import os

from dotenv import load_dotenv

from chat_agent.stub_llm import StubCalculatorModel, StubChitchatModel

load_dotenv()

GROQ_MODEL = "openai/gpt-oss-120b"
STUB_ENV_VAR = "LANGTEST_EXAMPLE_STUB"


def use_stub() -> bool:
    if os.environ.get(STUB_ENV_VAR, "").lower() in ("1", "true", "yes"):
        return True
    return not os.environ.get("GROQ_API_KEY")


def get_chitchat_model():
    if use_stub():
        return StubChitchatModel()
    from langchain_groq import ChatGroq

    return ChatGroq(model=GROQ_MODEL, temperature=0)


def get_calculator_model():
    if use_stub():
        return StubCalculatorModel()
    from langchain_groq import ChatGroq

    return ChatGroq(model=GROQ_MODEL, temperature=0)
