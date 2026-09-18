import re

_CALC_HINT = re.compile(
    r"[-+*/]|\b(add|subtract|minus|plus|times|multiply|divide|divided|random\w*)\b",
    re.IGNORECASE,
)


def classify(text: str) -> str:
    return "calculator" if _CALC_HINT.search(text) else "chitchat"
