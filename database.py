import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

server = os.getenv("DB_SERVER")
database = os.getenv("DB_NAME")
username = os.getenv("DB_USERNAME")
password = os.getenv("DB_PASSWORD")

connection_string = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={server};DATABASE={database};UID={username};PWD={password}"
)

def get_db_connection():
    return pyodbc.connect(connection_string)

def get_user_profile(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM UserProfile WHERE user_id = ?", user_id)
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "user_id": row.user_id,
            "name": row.name,
            "age": row.age,
            "sex": row.sex,
            "health_goals": row.health_goals,
            "last_updated": row.last_updated
        }
    return {}

def get_latest_user_health_entry(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT TOP 1 * FROM UserHealthData
        WHERE user_id = ?
        ORDER BY timestamp DESC
    """, user_id)
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "user_id": row.user_id,
            "entry_id": row.entry_id,
            "timestamp": row.timestamp,
            "age": row.age,
            "sex": row.sex,
            "symptoms": row.symptoms,
            "habits": row.habits,
            "health_goals": row.health_goals,
            "recommendations": row.recommendations,
            "follow_up_questions": row.follow_up_questions
        }
    return {}
