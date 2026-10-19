import requests
import time

url = "http://127.0.0.1:8000/ask"

test_queries = [
    "I'm getting NameError: name 'x' is not defined",
    "What is recursion in Python?",
    "Give me a hint for fixing IndexError",
    "What is Docker?"
]

print("Testing CodeLens AI API\n" + "="*50)

for query in test_queries:
    payload = {
        "student_id": "test_student",
        "query": query
    }
    
    start = time.time()
    response = requests.post(url, json=payload)
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