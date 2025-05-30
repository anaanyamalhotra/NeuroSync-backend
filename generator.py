from pydantic import BaseModel
from typing import List, Optional, Dict
import json, os, random
from datetime import datetime
import requests
import difflib

# === Load fragrance notes JSON ===
with open(os.path.join(os.path.dirname(__file__), "fragrance_notes.json"), "r") as f:
    fragrance_db = json.load(f)

# === Scent and Stress Maps ===
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

# === Input Model (Packet-Based) ===
class TwinRequest(BaseModel):
    name: str
    email: str
    job_title: str
    company: str
    career_goals: str
    productivity_limiters: str
    scent_note: str
    childhood_scent: str

# === Helper Functions ===
def infer_gender(name):
    try:
        res = requests.get(f"https://api.genderize.io?name={name.split()[0]}")
        if res.status_code == 200:
            return res.json().get("gender", "neutral")
    except:
        return "neutral"

def infer_life_stage(job_title: str, goals: str) -> str:
    text = f"{job_title} {goals}".lower()
    if any(k in text for k in ["student", "intern", "trainee"]):
        return "young_adult"
    elif any(k in text for k in ["manager", "executive", "founder"]):
        return "adult"
    elif "retired" in text:
        return "senior"
    return "adult"

def get_fragrance_notes(scent: str):
    normalized = scent.lower().strip()
    if normalized in fragrance_db:
        return fragrance_db[normalized]
    else:
        closest = get_closest_scent(normalized)
        if closest:
            print(f"[Fallback] Scent '{scent}' not found. Using closest match: '{closest}'")
            return fragrance_db[closest]
        return []

def get_closest_scent(input_scent: str):
    scent_keys = list(fragrance_db.keys())
    matches = difflib.get_close_matches(input_scent, scent_keys, n=1, cutoff=0.5)
    return matches[0] if matches else None

def apply_modifiers(base: Dict[str, float], modifiers: Dict[str, float]):
    for k, v in modifiers.items():
        base[k] = base.get(k, 0.5) + v

# === Journal Logging ===
def log_journal_entry(data: TwinRequest, output: dict):
    log_dir = "journal_logs"
    os.makedirs(log_dir, exist_ok=True)
    filename = data.email.replace("@", "_at_") + ".txt"
    with open(os.path.join(log_dir, filename), "a") as f:
        f.write(f"""
Timestamp: {output['timestamp']}
Name: {data.name}
Gender: {output['gender']}
Life Stage: {output['life_stage']}
Neurotransmitters: {output['neurotransmitters']}
Reflection Tags: {output.get('reflection_tags', [])}
Suggested Game: {output.get('xbox_game', 'N/A')}
Suggested Playlist: {output.get('spotify_playlist', 'N/A')}
-------------------------
""")

# === Vector Generation ===
def generate_twin_vector(data: TwinRequest):
    # Random baselines
    baseline_nt = {
        "dopamine": 0.55,
        "serotonin": 0.60,
        "oxytocin": 0.50,
        "GABA": 0.45,
        "cortisol": 0.40
    }
    nt = {}
    for k, base in baseline_nt.items():
        noise = random.uniform(-0.05, 0.05)
        nt[k] = round(min(1, max(0, base + noise)), 2)
    
    gender = infer_gender(data.name)
    if gender == "female":
        nt["oxytocin"] += 0.05
    elif gender == "male":
        nt["dopamine"] += 0.05

    life_stage = infer_life_stage(data.job_title, data.career_goals)

    # Scent modifiers
    for note in get_fragrance_notes(data.scent_note):
        apply_modifiers(nt, scent_map.get(note, {}))
    
    # Productivity limiter keywords
    for word in data.productivity_limiters.lower().split():
        apply_modifiers(nt, stress_map.get(word.strip(), {}))
    
    # Clamp to [0, 1]
    for k in nt:
        nt[k] = round(min(1, max(0, nt[k])), 2)

    # Brain regions
    brain_regions = {
        "amygdala": round((nt["cortisol"] + nt["oxytocin"]) / 2, 2),
        "prefrontal_cortex": round((nt["dopamine"] + nt["serotonin"]) / 2, 2),
        "hippocampus": round((nt["serotonin"] + nt["GABA"]) / 2, 2),
        "hypothalamus": round((nt["GABA"] + nt["cortisol"]) / 2, 2)
    }

    subvectors = {
        "amygdala": {
            "emotional_memory": round((nt["oxytocin"] + nt["cortisol"]) / 2, 2),
            "threat_detection": nt["cortisol"]
        },
        "prefrontal_cortex": {
            "planning": nt["dopamine"],
            "focus": round((nt["dopamine"] + nt["serotonin"]) / 2, 2)
        },
        "hippocampus": {
            "memory_encoding": nt["serotonin"],
            "spatial_navigation": nt["GABA"]
        },
        "hypothalamus": {
            "stress_response": round((nt["cortisol"] + nt["GABA"]) / 2, 2),
            "emotional_regulation": nt["GABA"]
        }
    }

    output = {
        "name": data.name,
        "gender": gender,
        "life_stage": life_stage,
        "neurotransmitters": nt,
        "brain_regions": brain_regions,
        "subvectors": subvectors,
        "timestamp": datetime.utcnow().isoformat(),
        "reflection_tags": [data.job_title, data.productivity_limiters, data.scent_note]  # used by reflection.py
    }

    log_journal_entry(data, output)
    return output
