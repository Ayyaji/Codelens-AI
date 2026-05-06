import time
from rag_core.router import route_query
from rag_core.agents import debug_agent, concept_agent, hint_agent, web_agent
from rag_core.kb_update import stage_for_approval
from rag_core.judgment import get_student_context, judge_response_level
from rag_core.session_logger import log_session

def run_pipeline(query: str, student_id: str = "anonymous") -> dict:
    # Step 1: Route
    agent_name = route_query(query)

    # Step 2: Judge student state
    context = get_student_context(student_id)
    directive = judge_response_level(query, agent_name, context)

    # Step 3: Run correct agent
    start = time.time()

    if agent_name == "debug":
        answer = debug_agent(query)

    elif agent_name == "concept":
        answer = concept_agent(query)

    elif agent_name == "hint":
        answer = hint_agent(query)

    else:  # web
        result = web_agent(query)
        if result["raw_content"]:
            stage_for_approval(
                query=query,
                content=result["raw_content"],
                source=result["source"]
            )
        answer = result["answer"]

    response_time = round(time.time() - start, 2)

    # Step 4: Log session
    log_session(
        student_id=student_id,
        query=query,
        agent_used=agent_name,
        response_time=response_time
    )

    return {
        "query": query,
        "agent_used": agent_name,
        "answer": answer,
        "directive": directive,
        "response_time": response_time
    }

if __name__ == "__main__":
    print("Testing judgment-aware pipeline...")
    result = run_pipeline(
        "I'm getting NameError: name 'x' is not defined",
        student_id="test_student"
    )
    print(f"Agent: {result['agent_used']}")
    print(f"Directive: {result['directive']}")
    print(f"Answer: {result['answer'][:200]}...")
    print(f"Time: {result['response_time']}s")