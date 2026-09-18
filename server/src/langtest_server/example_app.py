"""Single point of contact with the app LangTest is currently wired to.

Knowing which node produced a checkpoint, or what a graph's topology looks
like, requires the graph's actual node/trigger structure — data that isn't
recoverable from checkpoint storage alone. LangTest targets exactly one app
today, so the server imports its graph builder directly instead of adding a
generic "import path" API for apps it doesn't support yet. Swap this import
(and the rest of this module) if LangTest is ever pointed at a different app.

This is not a formal pyproject dependency: chat-agent depends on langtest
(sdk), which depends on langtest-server, so a declared edge back to
chat-agent would be circular. It resolves at import time only because uv's
workspace installs every member into one shared environment.
"""

from chat_agent.graph import build_graph

__all__ = ["build_graph"]
