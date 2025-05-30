from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import os
import random
import requests
from openai import OpenAI
from generator import generate_twin_vector, infer_gender_from_name, apply_modifiers, extract_keywords

# === INIT ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Load static data ===
with open(os.path.join(os.path.dirname(__file__), "fragrance_notes.json"), "r") as f:
    fragrance_db = json.load(f)

with open(os.path.join(os.path.dirname(__file__), "game_profiles.json"), "r") as f:
    game_profiles = json.load(f)

# === Scent + Stress Maps ===
scent_map = {
    "lavender": {"GABA": 0.1},
    "vanilla": {"oxytocin": 0.1},
    "mint": {"dopamine": 0.1},
    "citrus": {"serotonin": 0.1},
    "rose": {"oxytocin": 0.1},
    "bergamot": {"serotonin": 0.1},
    "cinnamon": {"dopamine": 0.1},
    "tonka bean": {"oxytocin": 0.1},
    "linalool": {"GABA": 0.1}
}

stress_map = {
    "deadline": {"cortisol": 0.2, "GABA": -0.1},
    "burnout": {"cortisol": 0.3, "dopamine": -0.1},
    "lonely": {"oxytocin": -0.2},
    "exam": {"cortisol": 0.2, "dopamine": 0.05},
    "overwhelmed": {"cortisol": 0.25, "GABA": -0.15}
}

# === Data models ===
class TwinRequest(BaseModel):
    name: str
    email: str
    job_title: Optional[str]
    company: Optional[str]
    career_goals: str
    productivity_limiters: str
    scent_note: str
    childhood_scent: str

class ReflectRequest(BaseModel):
    name: str
    current_emotion: str
    recent_events: str
    goals: str
    neurotransmitters: dict
    xbox_game: Optional[str] = None
    game_mode: Optional[str] = None
    duration_minutes: Optional[int] = None
    switch_time: Optional[str] = None

# === Utility ===
def get_fragrance_notes(scent):
    return fragrance_db.get(scent.lower().strip(), [])

def match_game(favorite_scent, stressors_text):
    scent = favorite_scent.lower().strip()
    stress_keywords = extract_keywords(stressors_text)
    candidates = [g for g in game_profiles if scent in g["scent_affinity"]]

    if not candidates:
        candidates = game_profiles

    game = random.choice(candidates)
    rationale = f"Matched based on your preference for '{scent}' and keywords like {', '.join(stress_keywords)}."

    return {
        "xbox_game": game["name"],
        "game_mode": random.choice(game["modes"]),
        "duration_minutes": random.randint(*game["duration_range"]),
        "switch_time": "After 30 mins" if "burnout" in stress_keywords else "After 20 mins",
        "spotify_playlist": game.get("spotify_playlist", "Focus Boost"),
        "match_reason": rationale
    }

# === API ROUTES ===
@app.post("/generate")
async def generate(data: TwinRequest):
    try:
        print("== ✅ Request received at /generate ==")
        twin = generate_twin_vector(data)
        game = match_game(data.scent_note, data.productivity_limiters)
        twin.update(game)
        twin["timestamp"] = datetime.utcnow().isoformat()
        print("== ✅ Final Output ==")
        return twin
    except Exception as e:
        print("❌ ERROR in /generate:", str(e))
        return {"error": str(e)}

@app.post("/reflect")
async def reflect(data: ReflectRequest):
    try:
        print("== Incoming Reflect Request ==")
        print(data)

        def analyze_neuro(nt):
            suggestions = []
            if nt.get("dopamine", 0.5) < 0.4:
                suggestions.append("Dopamine is low — try mint or cinnamon, or celebrate small wins.")
            if nt.get("serotonin", 0.5) < 0.4:
                suggestions.append("Low serotonin? Sunshine, citrus scents, or journaling may help.")
            if nt.get("oxytocin", 0.5) < 0.4:
                suggestions.append("Oxytocin seems low — reconnect with friends or try vanilla or rose scents.")
            if nt.get("GABA", 0.5) < 0.4:
                suggestions.append("GABA is low. Try lavender, quiet time, or calming music.")
            if nt.get("cortisol", 0.5) > 0.7:
                suggestions.append("Cortisol is high — breathe deeply, take breaks, and avoid multitasking.")
            return suggestions

        def local_fallback():
            insights = analyze_neuro(data.neurotransmitters)
            game_reco = f"🎮 Play: {data.xbox_game or 'a focus-friendly game'} ({data.game_mode}), for ~{data.duration_minutes} mins. Switch: {data.switch_time}."
            tips = "\n".join(f"- {tip}" for tip in insights)
            return f"""
🧠 Today’s Reflection for {data.name}  
Your brain chemistry suggests:  
{tips}

{game_reco}  
Stay mindful and pace your energy today.
"""

        # Build GPT prompt
        def build_prompt():
            insights = analyze_neuro(data.neurotransmitters or {})
            joined_insights = "\n".join(insights)
            game_reco = f"Today’s game: {data.xbox_game} ({data.game_mode}), play for ~{data.duration_minutes} minutes, then switch: {data.switch_time}."
            playlist = f"We’ve also curated a Spotify playlist for today: {data.name}'s {data.game_mode} Vibes 🎶"
            return (
                f"My name is {data.name}. I feel {data.current_emotion}. "
                f"Recent events include: {data.recent_events}. My goals are: {data.goals}. "
                f"Based on my brain chemistry, here's what's going on: {joined_insights}. "
                f"{game_reco} Suggest a daily routine, calming scent and a Spotify playlist to help."
            )

        prompt = build_prompt()

        # Call GPT
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You're a motivational mental wellness coach who interprets emotional state, brain chemistry, "
                        "and gaming focus to offer an uplifting reflection with practical guidance. Keep it kind, clear, and actionable."
                    )
                },
                {"role": "user", "content": prompt}
            ]
        )

        journal = response.choices[0].message.content.strip()

        if not journal:
            raise ValueError("GPT returned empty response")

        return {"journal_entry": journal}

    except Exception as e:
        print("❌ GPT fallback triggered due to:", e)
        return {"journal_entry": local_fallback()}
