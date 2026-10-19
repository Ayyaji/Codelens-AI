"""Lazy exports for the tutoring agents.

Importing this package does not build Groq or embedding clients.
"""


def __getattr__(name):
    if name == "debug_agent":
        from rag_core.agents.debug import debug_agent

        return debug_agent
    if name == "concept_agent":
        from rag_core.agents.concept import concept_agent

        return concept_agent
    if name == "hint_agent":
        from rag_core.agents.hint import hint_agent

        return hint_agent
    if name == "web_agent":
        from rag_core.agents.web import web_agent

        return web_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["debug_agent", "concept_agent", "hint_agent", "web_agent"]
