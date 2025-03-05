import openai
import os
import re
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Load OpenAI API key
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
google_creds = json.loads(os.getenv("GOOGLE_SHEETS_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_creds, scope)
client_gspread = gspread.authorize(creds)
sheet = client_gspread.open("AI Fitness Bot Workouts").sheet1

# User workout history and ongoing conversation storage
user_workout_history = {}
user_pending_requests = {}
user_feedback = {}

# List of common muscle groups
MUSCLE_GROUPS = [
    "chest", "back", "shoulders", "biceps", "triceps", "legs", "core", "abs", "glutes", "calves"
]

# Data Models
class WorkoutRequest(BaseModel):
    goal: str
    muscle_groups: list[str]
    length: str
    difficulty: str

class WorkoutLog(BaseModel):
    user: str
    muscle_groups: list[str]
    completed_exercises: list[str]
    skipped_exercises: list[str]
    reasons: list[str]

# API Routes
@app.post("/generate_workout")
def generate_workout(request: WorkoutRequest):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a fitness coach that generates detailed workout plans."},
                {"role": "user", "content": f"Create a {request.goal} workout focusing on {', '.join(request.muscle_groups)}, lasting {request.length}, for a {request.difficulty} level lifter."}
            ]
        )
        workout_plan = response.choices[0].message.content
        return {"workout_plan": workout_plan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/log_workout")
def log_workout(request: WorkoutLog):
    try:
        today = datetime.today().strftime('%Y-%m-%d')
        sheet.append_row([
            today, request.user, ", ".join(request.muscle_groups), ", ".join(request.completed_exercises), ", ".join(request.skipped_exercises), ", ".join(request.reasons)
        ])
        return {"message": "Workout logged successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
