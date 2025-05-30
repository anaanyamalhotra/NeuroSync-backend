from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import os
import random
import requests

app = FastAPI()

# === CORS settings ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Load fragrance notes and game profiles ===
with open(os.path.join(os.path.dirname(__file__), "fragrance_notes.json"), "r") as f:
    fragrance_db = json.load(f)

with open(os.path.join(os.path.dirname(__file__), "game_profiles.json"), "r") as f:
    game_profiles = json.load(f)

# === Mappings ===
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

# === Request schemas (7-question model only) ===
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

# === Helper functions ===
def get_fragrance_notes(scent):
    return fragrance_db.get(scent.lower().strip(), [])

def infer_gender_from_name(name):
    try:
        res = requests.get(f"https://api.genderize.io?name={name.split()[0]}")
        if res.status_code == 200:
            return res.json().get("gender")
    except:
        return None

def apply_modifiers(base, modifiers):
    for nt, val in modifiers.items():
        base[nt] = base.get(nt, 0.5) + val

def extract_keywords(text):
    # very basic keyword matcher for stress map
    return [k for k in stress_map if k in text.lower()]

def generate_twin_vector(data: TwinRequest):
    nt = {
        "dopamine": 0.5,
        "serotonin": 0.5,
        "oxytocin": 0.5,
        "GABA": 0.5,
        "cortisol": 0.5
    }

    gender = infer_gender_from_name(data.name)
    if gender == "female":
        nt["oxytocin"] += 0.05
    elif gender == "male":
        nt["dopamine"] += 0.05

    # Apply scent modifiers
    notes = get_fragrance_notes(data.scent_note)
    for note in notes:
        apply_modifiers(nt, scent_map.get(note, {}))

    # Extract stress-related keywords and apply effects
    stress_keywords = extract_keywords(data.productivity_limiters)
    for keyword in stress_keywords:
        apply_modifiers(nt, stress_map.get(keyword.lower(), {}))

    for k in nt:
        nt[k] = max(0, min(1, nt[k]))

    brain_regions = {
        "amygdala": (nt["cortisol"] + nt["oxytocin"]) / 2,
        "prefrontal_cortex": (nt["dopamine"] + nt["serotonin"]) / 2,
        "hippocampus": (nt["serotonin"] + nt["GABA"]) / 2,
        "hypothalamus": (nt["GABA"] + nt["cortisol"]) / 2
    }

    subvectors = {
        "amygdala": {
            "emotional_memory": round((nt["oxytocin"] + nt["cortisol"]) / 2, 2),
            "threat_detection": round(nt["cortisol"], 2)
        },
        "prefrontal_cortex": {
            "planning": round(nt["dopamine"], 2),
            "focus": round((nt["dopamine"] + nt["serotonin"]) / 2, 2)
        },
        "hippocampus": {
            "memory_encoding": round(nt["serotonin"], 2),
            "spatial_navigation": round(nt["GABA"], 2)
        },
        "hypothalamus": {
            "stress_response": round((nt["cortisol"] + nt["GABA"]) / 2, 2),
            "emotional_regulation": round(nt["GABA"], 2)
        }
    }

    return {
        "name": data.name,
        "gender": gender,
        "neurotransmitters": nt,
        "brain_regions": brain_regions,
        "subvectors": subvectors,
        "timestamp": datetime.utcnow().isoformat()
    }

def match_game(favorite_scent, stressors_text):
    scent = favorite_scent.lower().strip()
    stress_keywords = extract_keywords(stressors_text)
    candidates = []

    for game in game_profiles:
        if scent in game["scent_affinity"]:
            candidates.append(game)

    if not candidates:
        candidates = game_profiles

    game = random.choice(candidates)

    return {
        "xbox_game": game["name"],
        "game_mode": random.choice(game["modes"]),
        "duration_minutes": random.randint(*game["duration_range"]),
        "switch_time": "After 30 minutes" if "burnout" in stress_keywords else "After 20 minutes",
        "spotify_playlist": game.get("spotify_playlist", "Focus Boost")
    }

# === API Routes ===
@app.post("/generate")
async def generate(data: TwinRequest):
    twin = generate_twin_vector(data)
    game = match_game(data.scent_note, data.productivity_limiters)
    twin.update(game)
    return twin

@app.post("/reflect")
async def reflect(data: ReflectRequest):
    journal = (
        f"Hi {data.name}, it seems you're feeling {data.current_emotion.lower()}. "
        f"Reflecting on recent events — {data.recent_events} — can help bring clarity. "
        f"Remember, staying focused on your goals like '{data.goals}' is a powerful step forward."
    )
    return {"journal_entry": journal}
