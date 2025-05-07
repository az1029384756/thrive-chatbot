import requests
import os
from dotenv import load_dotenv

load_dotenv()

AZURE_AI_ENDPOINT = os.getenv("AZURE_AI_ENDPOINT")
AZURE_AI_KEY = os.getenv("AZURE_AI_KEY")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME")

def query_openai(prompt):
    url = f"{AZURE_AI_ENDPOINT}/language/:query-text?api-version=2024-04-01-preview"

    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": AZURE_AI_KEY
    }

    data = {
        "kind": "Conversation",
        "analysisInput": {
            "conversationItem": {
                "participantId": "user1",
                "id": "1",
                "modality": "text",
                "language": "en",
                "text": prompt
            },
            "isLoggingEnabled": False
        },
        "parameters": {
            "deploymentName": AZURE_DEPLOYMENT_NAME,
            "temperature": 0.7,
            "topP": 0.95,
            "maxTokens": 800
        }
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()

    return response.json()["result"]["response"]
