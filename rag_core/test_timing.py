"""Manual timing check for the guidance pipeline.

Run from the repository root after GROQ_API_KEY is set. This calls the live model.
"""

import time

from rag_core.agents.concept import concept_agent
from rag_core.agents.debug import debug_agent
from rag_core.agents.hint import hint_agent
from rag_core.agents.web import web_agent
from rag_core.router import route_query


def test_with_timing(query: str):
    print(f"\nQuery: {query}")
    print("=" * 60)
    start = time.time()
    agent_name = route_query(query)
    routing_time = round(time.time() - start, 2)
    print(f"1. Routing: {routing_time}s -> Agent: {agent_name}")

    start = time.time()
    if agent_name == "debug":
        answer = debug_agent(query)
    elif agent_name == "concept":
        answer = concept_agent(query)
    elif agent_name == "hint":
        answer = hint_agent(query)
    else:
        answer = web_agent(query)["answer"]
    agent_time = round(time.time() - start, 2)
    print(f"2. Agent execution: {agent_time}s")
    print(f"3. TOTAL: {routing_time + agent_time}s")
    print(f"\nAnswer: {answer[:150]}...")
    print("=" * 60)


if __name__ == "__main__":
    print("CodeLens AI — guidance timing")
    for query in [
        "I'm getting NameError: name 'x' is not defined",
        "What is recursion in Python?",
        "Give me a hint for fixing IndexError",
        "What is the capital of France?",
    ]:
        test_with_timing(query)
