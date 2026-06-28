import requests

url = "http://127.0.0.1:8000/ask"
payload = {
    "student_id": "verify_test",
    "query": "I'm getting NameError: name 'x' is not defined",
}

for i in range(3):
    r = requests.post(url, json=payload)
    data = r.json()
    print(f"Run {i + 1}: directive={data['directive']}, agent={data['agent_used']}")
    print(f"  Answer starts: {data['answer'][:150]}")
    print()
