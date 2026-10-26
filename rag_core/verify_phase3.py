import os

import requests

url = "http://127.0.0.1:8000/ask"
token = os.getenv("CODELENS_TOKEN", "")
payload = {"query": "I'm getting NameError: name 'x' is not defined"}
headers = {"Authorization": f"Bearer {token}"} if token else {}

for i in range(3):
    r = requests.post(url, json=payload, headers=headers)
    data = r.json()
    print(f"Run {i + 1}: directive={data['directive']}, agent={data['agent_used']}")
    print(f"  Answer starts: {data['answer'][:150]}")
    print()
