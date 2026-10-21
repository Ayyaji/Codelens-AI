import os
import time

import requests

url = "http://127.0.0.1:8000/ask"
token = os.getenv("CODELENS_TOKEN", "")
headers = {"Authorization": f"Bearer {token}"} if token else {}

test_queries = [
    "I'm getting NameError: name 'x' is not defined",
    "What is recursion in Python?",
    "Give me a hint for fixing IndexError",
    "What is Docker?"
]

print("Testing CodeLens AI API\n" + "="*50)
if not token:
    print("Set CODELENS_TOKEN to a bearer token from POST /auth/login.")

for query in test_queries:
    payload = {"query": query}
    
    start = time.time()
    response = requests.post(url, json=payload, headers=headers)
    total_time = round(time.time() - start, 2)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nQuery: {query}")
        print(f"Agent: {data['agent_used']}")
        print(f"Answer: {data['answer'][:150]}...")
        print(f"⏱️  Response time: {total_time}s")
    else:
        print(f"Error: {response.status_code}")

print("\n" + "="*50)
print("✅ API test complete")