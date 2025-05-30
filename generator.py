from pydantic import BaseModel
from typing import List, Optional, Dict
import re
import json
import os
from datetime import datetime
import requests
from textblob import TextBlob
import tldextract
import psycopg2

# === Load fragrance notes JSON ===
with open(os.path.join(os.path.dirname(__file__), "fragrance_notes.json"), "r") as f:
    fragrance_db = json.load(f)

# === Mapping Tables ===
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

class TwinRequest(BaseModel):
    name: str
    age: int
    gender: str
    scent_note: str
    childhood_scent: str
    stress_keywords: List[str]
    email: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    career_goals: Optional[str] = None
    productivity_limiters: Optional[str] = None
    routine_description: Optional[str] = None
    region: Optional[str] = None

# === Scent + Stress Effects ===
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

# === Helper Functions ===
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

def infer_life_stage(job_title: str, career_goals: str) -> str:
    text = f"{job_title} {career_goals}".lower()

    if any(term in text for term in ["intern", "student", "graduate", "entry level"]):
        return "young_adult"
    elif any(term in text for term in ["manager", "executive", "founder", "startup", "mid-career", "promotion"]):
        return "adult"
    elif any(term in text for term in ["retired", "veteran", "consultant", "legacy"]):
        return "senior"
    else:
        return "adult"

def log_journal_entry(data: TwinRequest, vector_output: dict):
    log_dir = "journal_logs"
    os.makedirs(log_dir, exist_ok=True)
    filename = data.email.replace("@", "_at_") + ".txt" if data.email else "anonymous_log.txt"
    log_path = os.path.join(log_dir, filename)

    entry = f"""
Timestamp: {vector_output['timestamp']}
Name: {data.name}
Age: {data.age}
Gender: {vector_output['gender']}
Neurotransmitters: {vector_output['neurotransmitters']}
Game: {vector_output.get("xbox_game", "N/A")}
Playlist: {vector_output.get("spotify_playlist", "N/A")}
Reflection: generated from Twin vector
----------------------------
"""
    with open(log_path, "a") as f:
        f.write(entry)

def generate_twin_vector(data: TwinRequest):
    nt = {
        "dopamine": round(random.uniform(0.45, 0.55), 2),
        "serotonin": round(random.uniform(0.45, 0.55), 2),
        "oxytocin": round(random.uniform(0.45, 0.55), 2),
        "GABA": round(random.uniform(0.45, 0.55), 2),
        "cortisol": round(random.uniform(0.45, 0.55), 2)
    }

    # Inferred gender tweak
    gender = infer_gender_from_name(data.name) or data.gender
    if gender == "female":
        nt["oxytocin"] += 0.05
    elif gender == "male":
        nt["dopamine"] += 0.05
    life_stage = infer_life_stage(data.job_title or "", data.career_goals or "")


    # Apply scent effects
    notes = get_fragrance_notes(data.scent_note)
    for note in notes:
        apply_modifiers(nt, scent_map.get(note, {}))

    # Apply stress keywords
    for keyword in data.stress_keywords:
        apply_modifiers(nt, stress_map.get(keyword.lower(), {}))

    # Clamp values to [0, 1]
    for k in nt:
        nt[k] = max(0, min(1, nt[k]))

    # Compute brain region activations
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
        "age": data.age,
        "gender": gender,
        "life_stage": life_stage, 
        "neurotransmitters": nt,
        "brain_regions": brain_regions,
        "subvectors": subvectors,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    log_journal_entry(data, output)

    return output
