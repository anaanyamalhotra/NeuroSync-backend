from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Define schema
class ReflectRequest(BaseModel):
    name: str
    current_emotion: str
    recent_events: str
    goals: str

@app.post("/reflect")
async def reflect(data: ReflectRequest):
    journal = (
        f"Hi {data.name}, it seems you're feeling {data.current_emotion.lower()}. "
        f"Reflecting on recent events — {data.recent_events} — can help bring clarity. "
        f"Remember, staying focused on your goals like '{data.goals}' is a powerful step forward."
    )
    return {"journal_entry": journal}
