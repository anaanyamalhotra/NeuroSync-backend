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

def generate_twin_vector(data: TwinRequest):
    nt = {
        "dopamine": 0.5,
        "serotonin": 0.5,
        "oxytocin": 0.5,
        "GABA": 0.5,
        "cortisol": 0.5
    }

    # Inferred gender tweak
    gender = infer_gender_from_name(data.name) or data.gender
    if gender == "female":
        nt["oxytocin"] += 0.05
    elif gender == "male":
        nt["dopamine"] += 0.05

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

    return {
        "name": data.name,
        "age": data.age,
        "gender": gender,
        "neurotransmitters": nt,
        "brain_regions": brain_regions,
        "timestamp": datetime.utcnow().isoformat()
    }
