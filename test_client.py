import requests
import json

url = "http://127.0.0.1:8000/v1/chat/completions"
payload = {
    "model": "gpt-3.5-turbo",
    "stream": True,
    "messages": [
        {"role": "user", "content": "Wyjaśnij w 2 zdaniach, co robi Gyroscope middleware."}
    ]
}
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer DUMMY"  # proxy i tak tego nie używa na razie
}

with requests.post(url, headers=headers, data=json.dumps(payload), stream=True) as r:
    for line in r.iter_lines():
        if not line:
            continue
        if line.startswith(b"data: "):
            data = line[len(b"data: "):]
            if data == b"[DONE]":
                print("\n[STREAM DONE]")
                break
            chunk = json.loads(data)
            delta = chunk["choices"][0]["delta"].get("content", "")
            print(delta, end="", flush=True)
