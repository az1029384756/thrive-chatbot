import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Pull variables from .env
deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME")
endpoint = os.getenv("AZURE_ENDPOINT")
api_key = os.getenv("AZURE_API_KEY")
api_version = os.getenv("AZURE_API_VERSION")

# Build URL
url = f"{endpoint}openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"

# Headers and payload
headers = {
    "Content-Type": "application/json",
    "api-key": api_key
}

payload = {
    "messages": [
        {"role": "system", "content": "You are a helpful AI health coach."},
        {"role": "user", "content": "I’ve been feeling fatigued. What should I do?"}
    ],
    "temperature": 0.7,
    "top_p": 1,
    "frequency_penalty": 0,
    "presence_penalty": 0,
    "max_tokens": 500
}

# Send POST request
response = requests.post(url, headers=headers, json=payload)

# Print response
if response.status_code == 200:
    reply = response.json()
    print("✅ Success:")
    print(reply["choices"][0]["message"]["content"])
else:
    print("❌ Failed:")
    print(f"Status Code: {response.status_code}")
    print(response.text)
