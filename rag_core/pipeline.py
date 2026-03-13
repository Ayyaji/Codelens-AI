from rag_core.router import route_query
from rag_core.agents import debug_agent, concept_agent, hint_agent, web_agent

def run_pipeline(query: str) -> dict:
    # Step 1: Route
    agent_name = route_query(query)
    
    # Step 2: Run correct agent
    if agent_name == "debug":
        answer = debug_agent(query)
    elif agent_name == "concept":
        answer = concept_agent(query)
    elif agent_name == "hint":
        answer = hint_agent(query)
    else:
        answer = web_agent(query)
    
    return {
        "query": query,
        "agent_used": agent_name,
        "answer": answer
    }

# Test
if __name__ == "__main__":
    queries = [
        "I'm getting TypeError: can only concatenate str to str",
        "What is a for loop?",
        "Just give me a hint for my IndentationError"
    ]
    
    for q in queries:
        print(f"\nQuery: {q}")
        result = run_pipeline(q)
        print(f"Agent: {result['agent_used']}")
        print(f"Answer: {result['answer'][:200]}...")
