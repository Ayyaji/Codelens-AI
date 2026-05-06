import time
from router import route_query
from agents import debug_agent, concept_agent, hint_agent, web_agent

def test_with_timing(query: str):
    print(f"\nQuery: {query}")
    print("="*60)
    
    # Step 1: Routing
    start = time.time()
    agent_name = route_query(query)
    routing_time = round(time.time() - start, 2)
    print(f"1. Routing: {routing_time}s → Agent: {agent_name}")
    
    # Step 2: Agent execution
    start = time.time()
    if agent_name == "debug":
        answer = debug_agent(query)
    elif agent_name == "concept":
        answer = concept_agent(query)
    elif agent_name == "hint":
        answer = hint_agent(query)
    else:  # web
        result = web_agent(query)
        answer = result["answer"]
    
    agent_time = round(time.time() - start, 2)
    print(f"2. Agent execution: {agent_time}s")
    
    total_time = routing_time + agent_time
    print(f"3. TOTAL: {total_time}s")
    print(f"\nAnswer: {answer[:150]}...")
    print("="*60)

# Test queries
print("CodeLens AI - Detailed Timing Breakdown")
print("="*60)

test_queries = [
    "I'm getting NameError: name 'x' is not defined",
    "What is recursion in Python?",
    "Give me a hint for fixing IndexError",
    "What is the capital of France?"  # Should route to web
]

for query in test_queries:
    test_with_timing(query)

print("\n✅ Timing analysis complete")