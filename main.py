from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "AI Fitness Backend is Running!"}

