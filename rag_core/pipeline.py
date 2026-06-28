import time

from rag_core.agents import concept_agent, debug_agent, hint_agent, web_agent
from rag_core.judgment import get_student_context, judge_response_level
from rag_core.kb_update import stage_for_approval
from rag_core.profiler import profiler, reset_profiler
from rag_core.router import route_query
from rag_core.session_logger import log_session


def run_pipeline(
    query: str, student_id: str = "anonymous", profile: bool = False
) -> dict:
    if profile:
        reset_profiler()

    # Step 1: Route
    with profiler.measure("1. Route query") if profile else _no_measure():
        agent_name = route_query(
            query,
        )

    # Step 2: Judge student state
    with profiler.measure("2. Get student context") if profile else _no_measure():
        context = get_student_context(student_id)

    with profiler.measure("3. Judge response level") if profile else _no_measure():
        directive = judge_response_level(query, agent_name, context)

    # Step 3: Run correct agent
    if agent_name == "debug":
        with profiler.measure("4a. Debug agent") if profile else _no_measure():
            answer = debug_agent(query, directive)

    elif agent_name == "concept":
        with profiler.measure("4b. Concept agent") if profile else _no_measure():
            answer = concept_agent(query, directive)

    elif agent_name == "hint":
        with profiler.measure("4c. Hint agent") if profile else _no_measure():
            answer = hint_agent(query, directive)

    else:  # web
        with profiler.measure("4d. Web agent") if profile else _no_measure():
            result = web_agent(query)
            if result["raw_content"]:
                stage_for_approval(
                    query=query, content=result["raw_content"], source=result["source"]
                )
            answer = result["answer"]

    # Step 4: Log session
    with profiler.measure("5. Log session") if profile else _no_measure():
        log_session(
            student_id=student_id,
            query=query,
            agent_used=agent_name,
            response_time=sum(profiler.timings.values()) if profile else 0,
        )

    result = {
        "query": query,
        "agent_used": agent_name,
        "answer": answer,
        "directive": directive,
        "response_time": sum(profiler.timings.values()) if profile else 0,
    }

    if profile:
        print(profiler.report())
        result["profiling"] = profiler.timings

    return result


class _no_measure:
    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass


if __name__ == "__main__":
    print("Testing judgment-aware pipeline...")
    result = run_pipeline(
        "I'm getting NameError: name 'x' is not defined", student_id="test_student"
    )
    print(f"Agent: {result['agent_used']}")
    print(f"Directive: {result['directive']}")
    print(f"Answer: {result['answer'][:200]}...")
    print(f"Time: {result['response_time']}s")
