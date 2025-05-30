from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow CORS (needed for Streamlit to call backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/reflect")
async def reflect(request: Request):
    data = await request.json()
    name = data.get("name")
    current_emotion = data.get("current_emotion")
    recent_events = data.get("recent_events")
    goals = data.get("goals")

    if not all([name, current_emotion, recent_events, goals]):
        return {"error": "Missing fields."}

    journal = (
        f"Hi {name}, it seems you're feeling {current_emotion.lower()}. "
        f"Reflecting on recent events — {recent_events} — can help bring clarity. "
        f"Remember, staying focused on your goals like '{goals}' is a powerful step forward."
    )

    return {"journal_entry": journal}
