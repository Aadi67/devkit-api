
import requests

BASE_URL = "http://127.0.0.1:8000"

# Validate JSON
response = requests.post(
    f"{BASE_URL}/v1/json/validate",
    json={"content": '{"hello": "world"}'}
)

print("JSON validation:", response.json())


# Generate UUIDs
response = requests.post(
    f"{BASE_URL}/v1/uuid",
    json={"count": 3}
)

print("Generated UUIDs:", response.json())


# Generate SHA-256
response = requests.post(
    f"{BASE_URL}/v1/hash/sha256",
    json={"content": "hello"}
)

print("SHA-256:", response.json())
