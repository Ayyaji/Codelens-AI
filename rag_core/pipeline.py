from rag_core.router import route_query
from rag_core.agents import debug_agent, concept_agent, hint_agent, web_agent
from rag_core.kb_update import stage_for_approval

def run_pipeline(query: str) -> dict:
    # Step 1: Route
    agent_name = route_query(query)
    
    # Step 2: Run correct agent
    if agent_name == "debug":
        answer = debug_agent(query)
        return {
            "query": query,
            "agent_used": agent_name,
            "answer": answer
        }
    
    elif agent_name == "concept":
        answer = concept_agent(query)
        return {
            "query": query,
            "agent_used": agent_name,
            "answer": answer
        }
    
    elif agent_name == "hint":
        answer = hint_agent(query)
        return {
            "query": query,
            "agent_used": agent_name,
            "answer": answer
        }
    
    else:  # web
        result = web_agent(query)
        
        # Stage for teacher approval if content found
        if result["raw_content"]:
            stage_for_approval(
                query=query,
                content=result["raw_content"],
                source=result["source"]
            )
        
        return {
            "query": query,
            "agent_used": "web",
            "answer": result["answer"]
        }


# Test
if __name__ == "__main__":
    print("Testing web pipeline...")
    result = run_pipeline("What is Docker in software development?")
    print(f"Agent: {result['agent_used']}")
    print(f"Answer: {result['answer'][:300]}...")