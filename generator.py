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
    "lavender": {"GABA": 0.15, "cortisol": -0.1},
    "vanilla": {"oxytocin": 0.1, "dopamine": 0.05},   
    "mint": {"dopamine": 0.12, "serotonin": 0.05},  
    "citrus": {"serotonin": 0.15, "cortisol": -0.05}, 
    "rose": {"oxytocin": 0.12, "GABA": 0.05},        
    "bergamot": {"serotonin": 0.12, "GABA": 0.08},   
    "cinnamon": {"dopamine": 0.15},     
    "tonka bean": {"oxytocin": 0.08, "dopamine": 0.04}, 
    "linalool": {"GABA": 0.18, "cortisol": -0.12}    
}

stress_map = {
    "deadline": {"cortisol": 0.25, "dopamine": -0.1}, 
    "burnout": {"cortisol": 0.35, "GABA": -0.15, "dopamine": -0.1}, 
    "lonely": {"oxytocin": -0.25, "serotonin": -0.1},   
    "exam": {"cortisol": 0.3, "dopamine": 0.05, "GABA": -0.05}, 
    "overwhelmed": {"cortisol": 0.4, "GABA": -0.2, "serotonin": -0.1},
    "uncertainty": {"cortisol": 0.2, "serotonin": -0.1},   
    "rejection": {"dopamine": -0.15, "oxytocin": -0.2},  
    "fatigue": {"dopamine": -0.1, "GABA": -0.1},  
    "multitasking": {"dopamine": -0.05, "serotonin": -0.05},
    "conflict": {"cortisol": 0.3, "oxytocin": -0.15}     
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

from textblob import TextBlob

def extract_keywords(text: str) -> List[str]:
    """Extracts noun-based keywords from input text using TextBlob POS tagging."""
    blob = TextBlob(text)
    return [word for word, tag in blob.tags if tag.startswith("NN")]

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
        "amygdala": round((nt["cortisol"] * 0.6 + nt["oxytocin"] * 0.4), 2),
        "prefrontal_cortex": round((nt["dopamine"] * 0.5 + nt["serotonin"] * 0.5), 2),
        "hippocampus": round((nt["serotonin"] * 0.6 + nt["GABA"] * 0.4), 2),
        "hypothalamus": round((nt["GABA"] * 0.5 + nt["cortisol"] * 0.5), 2)
    }

    lowest_region = min(brain_regions, key=brain_regions.get)
    region_scent_suggestions = {
        "amygdala": "lavender or rose for emotional grounding",
        "prefrontal_cortex": "mint or cinnamon for enhanced focus",
        "hippocampus": "bergamot or citrus for memory support",
        "hypothalamus": "linalool or vanilla for emotional balance"
    }
    scent_reinforcement = region_scent_suggestions.get(lowest_region, "any calming scent you enjoy")

    subvectors = {
        "amygdala": {
            "emotional_memory": round((nt["oxytocin"] * 0.6 + nt["cortisol"] * 0.4), 2),
            "threat_detection": round(nt["cortisol"], 2)
        },
        "prefrontal_cortex": {
            "planning": round(nt["dopamine"], 2),
            "focus": round((nt["dopamine"] * 0.6 + nt["serotonin"] * 0.4), 2)
        },
        "hippocampus": {
            "memory_encoding": round(nt["serotonin"], 2),
            "spatial_navigation": round(nt["GABA"], 2)
        },
        "hypothalamus": {
            "stress_response": round((nt["cortisol"] * 0.7 + nt["GABA"] * 0.3), 2),
            "emotional_regulation": round(nt["GABA"], 2)
        }
    }

    dominant_nt = max(nt, key=nt.get)
    if dominant_nt == "dopamine":
        spotify_playlist = "Upbeat Drive | Motivation Boost"
    elif dominant_nt == "serotonin":
        spotify_playlist = "Sunny Mornings | Mood Boosters"
    elif dominant_nt == "oxytocin":
        spotify_playlist = "Romantic Acoustics | Cozy Evenings"
    elif dominant_nt == "GABA":
        spotify_playlist = "Lofi Chill | Relax & Study"
    elif dominant_nt == "cortisol" and nt["cortisol"] > 0.6:
        spotify_playlist = "Calm Nature | Stress Recovery"
    else:
        spotify_playlist = "Neural Flow | Balanced Focus"
        
    if nt["dopamine"] > 0.6 and nt["cortisol"] < 0.5:
        xbox_game = "Forza Horizon 5"
        game_mode = "exploration"
        duration_minutes = 40
        switch_time = "every 20 mins"
    elif nt["cortisol"] > 0.6:
        xbox_game = "Stardew Valley"
        game_mode = "relaxation"
        duration_minutes = 30
        switch_time = "every 15 mins"
    elif nt["GABA"] < 0.4:
        xbox_game = "ABZÛ"
        game_mode = "meditative"
        duration_minutes = 25
        switch_time = "every 10 mins"
    elif nt["serotonin"] < 0.45:
        xbox_game = "Ori and the Blind Forest"
        game_mode = "narrative challenge"
        duration_minutes = 35
        switch_time = "every 20 mins"
    else:
        xbox_game = "Rocket League"
        game_mode = "team coordination"
        duration_minutes = 30
        switch_time = "every 15 mins"

    output = {
        "name": data.name,
        "gender": gender,
        "life_stage": life_stage,
        "neurotransmitters": nt,
        "brain_regions": brain_regions,
        "subvectors": subvectors,
        "timestamp": datetime.utcnow().isoformat(),
        "reflection_tags": [data.job_title, data.productivity_limiters, data.scent_note],
        "xbox_game": xbox_game,
        "game_mode": game_mode,
        "duration_minutes": duration_minutes,
        "switch_time": switch_time,
        "spotify_playlist": spotify_playlist,
        "scent_reinforcement": scent_reinforcement,
    }

    required_keys = ["neurotransmitters", "xbox_game", "game_mode", "duration_minutes", "switch_time", "spotify_playlist"]
    for key in required_keys:
        if key not in output:
            raise ValueError(f"[BUG] Missing key in generate_twin_vector output: {key}")

    print("✅ FINAL OUTPUT from generate_twin_vector:", output)

    log_journal_entry(data, output)
    return output
