import azure.functions as func
import json
import os
from dotenv import load_dotenv
from database import get_user_profile, get_latest_user_health_entry
from openai_handler import query_openai

load_dotenv()

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        user_id = req.params.get('user_id')
        if not user_id:
            return func.HttpResponse("Missing user_id", status_code=400)

        user_profile = get_user_profile(user_id)
        health_data = get_latest_user_health_entry(user_id)

        message = req.get_json().get("message")

        if not message:
            return func.HttpResponse("Missing message", status_code=400)

        prompt = f"""
You are a compassionate AI health coach. Provide thoughtful, personalized advice based on the user’s data.

User Profile:
Name: {user_profile.get("name")}
Age: {user_profile.get("age")}
Sex: {user_profile.get("sex")}
Health Goals: {user_profile.get("health_goals")}

Latest Entry:
Symptoms: {health_data.get("symptoms")}
Habits: {health_data.get("habits")}

Message:
{message}
"""

        response = query_openai(prompt)

        return func.HttpResponse(json.dumps({"response": response}), mimetype="application/json")

    except Exception as e:
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
