"""Guidance pipeline: route, judge, answer, log.

Used by POST /ask. Job-description upload and tests live in the agents package
and are called directly by the API.
"""

import time

from rag_core.judgment import get_student_context, judge_response_level
from rag_core.kb_update import stage_for_approval
from rag_core.profiler import profiler, reset_profiler
from rag_core.router import route_query
from rag_core.session_logger import log_session


class _no_measure:
    def __enter__(self):
        return None

    def __exit__(self, *args):
        return False


def run_pipeline(query: str, student_id: str = "anonymous", profile: bool = False) -> dict:
    """Answer one guidance question and record the turn."""
    started = time.perf_counter()
    if profile:
        reset_profiler()

    with profiler.measure("1. Route query") if profile else _no_measure():
        agent_name = route_query(query)

    with profiler.measure("2. Get student context") if profile else _no_measure():
        context = get_student_context(student_id)

    with profiler.measure("3. Judge response level") if profile else _no_measure():
        directive = judge_response_level(query, agent_name, context)

    from rag_core.agents.concept import concept_agent
    from rag_core.agents.debug import debug_agent
    from rag_core.agents.hint import hint_agent
    from rag_core.agents.web import web_agent

    if agent_name == "debug":
        with profiler.measure("4a. Debug agent") if profile else _no_measure():
            answer = debug_agent(query, directive)
    elif agent_name == "concept":
        with profiler.measure("4b. Concept agent") if profile else _no_measure():
            answer = concept_agent(query, directive)
    elif agent_name == "hint":
        with profiler.measure("4c. Hint agent") if profile else _no_measure():
            answer = hint_agent(query, directive)
    else:
        with profiler.measure("4d. Web agent") if profile else _no_measure():
            result = web_agent(query)
            if result["raw_content"]:
                stage_for_approval(
                    query=query,
                    content=result["raw_content"],
                    source=result["source"],
                )
            answer = result["answer"]

    elapsed = round(time.perf_counter() - started, 3)
    with profiler.measure("5. Log session") if profile else _no_measure():
        log_session(
            student_id=student_id,
            query=query,
            agent_used=agent_name,
            response_time=elapsed,
        )

    result = {
        "query": query,
        "agent_used": agent_name,
        "answer": answer,
        "directive": directive,
        "response_time": elapsed,
    }
    if profile:
        print(profiler.report())
        result["profiling"] = dict(profiler.timings)
    return result
