import openai
import os
import re
import gspread
import json
import uvicorn
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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
user_muscle_group_tracking = {}

# List of common muscle groups
MUSCLE_GROUPS = [
    "chest", "back", "shoulders", "biceps", "triceps", "legs", "core", "abs", "glutes", "calves"
]

# Data Models
class WorkoutRequest(BaseModel):
    user: str
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
        # Track muscle group frequency
        if request.user not in user_muscle_group_tracking:
            user_muscle_group_tracking[request.user] = {}
        for group in request.muscle_groups:
            user_muscle_group_tracking[request.user][group] = datetime.today()

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a fitness coach that generates detailed workout plans."},
                {"role": "user", "content": f"Create a {request.goal} workout focusing on {', '.join(request.muscle_groups)}, lasting {request.length}, for a {request.difficulty} level lifter."}
            ]
        )
        workout_plan = response.choices[0].message.content
        user_workout_history[request.user] = request.muscle_groups
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

        # Store user feedback for adaptation
        if request.user not in user_feedback:
            user_feedback[request.user] = []
        user_feedback[request.user].append({
            "completed": request.completed_exercises,
            "skipped": request.skipped_exercises,
            "reasons": request.reasons
        })

        return {"message": "Workout logged successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/suggest_muscle_groups")
def suggest_muscle_groups(user: str):
    if user not in user_muscle_group_tracking:
        return {"message": "No workout history found. Try logging some workouts first."}
    
    today = datetime.today()
    overdue_muscles = []
    for muscle, last_trained in user_muscle_group_tracking[user].items():
        if today - last_trained > timedelta(days=7):  # Suggest if muscle hasn't been trained in 7+ days
            overdue_muscles.append(muscle)
    
    if not overdue_muscles:
        return {"message": "Your workout balance looks great!"}
    else:
        return {"suggested_muscle_groups": overdue_muscles}

# Health Check Route
@app.get("/")
def read_root():
    return {"message": "API is running successfully!"}

# Run the FastAPI app with Uvicorn
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)

