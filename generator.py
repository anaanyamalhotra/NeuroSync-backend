

from pydantic import BaseModel
from typing import List, Optional, Dict
import json, os, random
from datetime import datetime
import requests
import difflib
import pandas as pd
from vector_store import load_metadata


# === Load fragrance notes JSON ===
with open(os.path.join(os.path.dirname(__file__), "fragrance_notes.json"), "r") as f:
    fragrance_db = json.load(f)

with open(os.path.join(os.path.dirname(__file__), "cultural_affinities.json"), "r") as f:
    cultural_affinities = json.load(f)

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
    "linalool": {"GABA": 0.18, "cortisol": -0.12},
    "musk": {"oxytocin": 0.1, "amygdala": 0.03},
    "androstadienone": {"dopamine": 0.12, "cortisol": 0.08, "amygdala": 0.06},
    "sandalwood": {"GABA": 0.1, "serotonin": 0.06},
    "amber": {"dopamine": 0.05, "oxytocin": 0.07}, 
    "jasmine": {"serotonin": 0.1, "oxytocin": 0.08},
    "cedarwood": {"GABA": 0.1, "cortisol": -0.05}, 
    "ylang ylang": {"oxytocin": 0.1, "dopamine": 0.06},
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
    assigned_sex: Optional[str] = "unspecified"

# === Helper Functions ===
def infer_gender(name):
    try:
        res = requests.get(f"https://api.genderize.io?name={name.split()[0]}")
        if res.status_code == 200:
            return res.json().get("gender", "neutral")
    except:
        return "neutral"

def infer_work_environment(email: str) -> str:
    domain = email.split("@")[-1].lower()
    if any(domain.startswith(p) for p in ["gmail", "yahoo", "outlook", "hotmail"]):
        return "general_consumer"
    elif "edu" in domain:
        return "academic"
    else:
        return "corporate"

def email_style_score(email: str) -> float:
    username = email.split("@")[0]
    score = 0
    if any(char.isdigit() for char in username):
        score -= 0.1
    if "." in username:
        score += 0.1
    if username.islower():
        score += 0.1
    if any(x in username.lower() for x in ["x", "lol", "420", "gamer"]):
        score -= 0.2
    return round(score, 2)

def verify_name_email_alignment(name: str, email: str) -> bool:
    email_username = email.split("@")[0].lower()
    name_parts = name.lower().split()
    return any(part in email_username for part in name_parts)

def infer_life_stage(age):
    if age < 13:
        return "child"
    elif 13 <= age < 18:
        return "teen"
    elif 18 <= age < 30:
        return "young_adult"
    elif 30 <= age < 50:
        return "adult"
    else:
        return "senior"

def infer_age_range(job_title: str, goals: str) -> str:
    text = f"{job_title} {goals}".lower()
    if any(k in text for k in ["student", "intern", "trainee"]):
        return "18-25"
    elif any(k in text for k in ["manager", "executive", "founder"]):
        return "25-40"
    elif "retired" in text:
        return "60+"
    return "25-40"

def apply_cultural_modifiers(nt: Dict[str, float], email: str, name: str):
    region = infer_region(email)
    work_env = infer_work_environment(email)
    style_score = email_style_score(email)
    alignment = verify_name_email_alignment(name, email)
    favored_scents = cultural_affinities.get(region, [])
    
    for scent in favored_scents:
        modifiers = scent_map.get(scent.lower(), {})
        for k, v in modifiers.items():
            nt[k] = min(1.0, max(0.0, nt.get(k, 0.5) + v * 0.05))

    return nt, region, work_env, style_score, alignment

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

def build_scent_profile(scent: str):
    notes = get_fragrance_notes(scent)
    nt_map = {}
    for note in notes:
        effects = scent_map.get(note.lower(), {})
        for nt in effects:
            nt_map.setdefault(nt, []).append(note)
    return {
        "scent": scent,
        "notes": notes,
        "neurotransmitter_map": nt_map
    }

def infer_life_stage_from_text(job_title: str, goals: str) -> str:
    text = f"{job_title} {goals}".lower()
    if any(k in text for k in ["student", "intern", "trainee"]):
        return "young_adult"
    elif any(k in text for k in ["manager", "executive", "founder"]):
        return "adult"
    elif "retired" in text:
        return "senior"
    return "adult"

def infer_region(email: str) -> str:
    if email.endswith(".in"):
        return "South Asia"
    if email.endswith(".jp") or email.endswith(".kr") or email.endswith(".cn"):
        return "East Asia"
    if email.endswith(".ae") or email.endswith(".sa"):
        return "Middle East"
    if email.endswith(".br") or email.endswith(".mx"):
        return "Latin America"
    if email.endswith(".fr") or email.endswith(".de") or email.endswith(".uk"):
        return "Europe"
    return "North America"

def extract_memory_scent_profile(childhood_memory: str, fragrance_db, scent_map):
    blob = TextBlob(childhood_memory.lower())
    nouns = [word for word, tag in blob.tags if tag in ("NN", "NNS", "NNP", "JJ")]

    extracted_notes = []
    for word in nouns:
        for base_note in fragrance_db:
            if word in base_note or base_note in word:
                extracted_notes.append(base_note)

    extracted_notes = list(set(extracted_notes))  # Deduplicate

    neurotransmitter_map = {}
    for note in extracted_notes:
        if note in scent_map:
            for nt in scent_map[note]:
                neurotransmitter_map.setdefault(nt, []).append(note)

    return {
        "memory_text": childhood_memory,
        "scent_notes": extracted_notes,
        "neuro_map": neurotransmitter_map,
        "linked_regions": ["hippocampus", "amygdala"]
    }

def infer_industry(job_title: str, company: str) -> str:
    text = f"{job_title} {company}".lower()
    if any(x in text for x in ["software", "engineer", "developer", "ai", "ml", "data"]):
        return "Tech"
    elif any(x in text for x in ["doctor", "nurse", "clinic", "hospital", "health"]):
        return "Healthcare"
    elif any(x in text for x in ["law", "attorney", "legal", "firm"]):
        return "Legal"
    elif any(x in text for x in ["finance", "investment", "bank", "analyst", "accountant"]):
        return "Finance"
    elif any(x in text for x in ["teacher", "professor", "school", "education"]):
        return "Education"
    else:
        return "General"

def analyze_circadian_rhythm(nt, timestamp):
    hour = datetime.fromisoformat(timestamp).hour
    circadian_window = (
        "morning" if 5 <= hour < 12 else
        "afternoon" if 12 <= hour < 17 else
        "evening" if 17 <= hour < 22 else
        "night"
    )

    circadian_note = []
    if circadian_window == "night" and nt["cortisol"] > 0.6:
        circadian_note.append("High cortisol at night may disrupt sleep. Try journaling, lavender, or screen breaks.")
    if circadian_window == "morning" and nt["GABA"] < 0.4:
        circadian_note.append("Low GABA in the morning may indicate unrestful sleep. Try exposure to sunlight and a consistent wake time.")
    if nt["dopamine"] > 0.7 and circadian_window == "night":
        circadian_note.append("Elevated dopamine late at night may reflect overstimulation. Consider a calming wind-down ritual.")

    return circadian_window, circadian_note

def get_closest_scent(input_scent: str):
    scent_keys = list(fragrance_db.keys())
    matches = difflib.get_close_matches(input_scent, scent_keys, n=1, cutoff=0.5)
    return matches[0] if matches else None

def apply_modifiers(base: Dict[str, float], modifiers: Dict[str, float]):
    for k, v in modifiers.items():
        base[k] = base.get(k, 0.5) + v

def determine_cognitive_focus(subvectors):
    region_strengths = {region: sum(values.values()) for region, values in subvectors.items()}
    dominant_region = max(region_strengths, key=region_strengths.get)
    focus_map = {
        "amygdala": "Emotional AI",
        "hippocampus": "Memory-Augmented NLP",
        "hypothalamus": "Adaptive Stress Interfaces",
        "prefrontal_cortex": "Cognitive Planning Systems"
    }
    return focus_map.get(dominant_region, "General Cognitive Modeling")

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
Assigned Sex: {data.assigned_sex}
Circadian Window: {output.get('circadian_window', 'N/A')}
Circadian Notes: {" | ".join(output.get('circadian_note', []))}
Neurotransmitters: {output['neurotransmitters']}
Reflection Tags: {output.get('reflection_tags', [])}
Suggested Game: {output.get('xbox_game', 'N/A')}
Suggested Playlist: {output.get('spotify_playlist', 'N/A')}
-------------------------
""")

# === Vector Generation ===
def generate_twin_vector(data: TwinRequest, goals_sentiment=None, stressors_sentiment=None):
    stress_categories = {
        "social": ["communication", "manager", "team", "conflict"],
        "workload": ["deadline", "overload", "multitasking", "burnout"],
        "environment": ["noise", "space", "distractions"]
    }
    classified_stressors = {"social": [], "workload": [], "environment": []}
    stress_words = extract_keywords(data.productivity_limiters)
    for word in stress_words:
        for category, terms in stress_categories.items():
            if word.lower() in terms:
                classified_stressors[category].append(word.lower())
    
    
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

    assigned_sex = getattr(data, "assigned_sex", "").lower()
    if assigned_sex == "female":
        nt["oxytocin"] += 0.07
        nt["serotonin"] += 0.02
        if "musk" in data.scent_note.lower():
            nt["amygdala"] = round(nt.get("amygdala", 0.5) - 0.03, 2)

    elif assigned_sex == "male":
        nt["dopamine"] += 0.05
        nt["cortisol"] += 0.03
        if "musk" in data.scent_note.lower() or "androstadienone" in data.scent_note.lower():
            nt["amygdala"] = round(nt.get("amygdala", 0.5) + 0.04, 2)

    life_stage = infer_life_stage_from_text(data.job_title, data.career_goals)
    age_range = infer_age_range(data.job_title, data.career_goals)
    name_parts = data.name.strip().split()
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[-1] if len(name_parts) > 1 else ""
    industry = infer_industry(data.job_title, data.company)

    # Scent modifiers
    for note in get_fragrance_notes(data.scent_note):
        apply_modifiers(nt, scent_map.get(note, {}))

    scent_profile = build_scent_profile(data.scent_note)

    keywords = extract_keywords(data.productivity_limiters)
    for word in keywords:
        if word.lower() in stress_map:
            apply_modifiers(nt, stress_map[word.lower()])

    if goals_sentiment is None:
        goals_blob = TextBlob(data.career_goals)
        goals_sentiment = goals_blob.sentiment.polarity

    if stressors_sentiment is None:
        stress_blob = TextBlob(data.productivity_limiters)
        stressors_sentiment = stress_blob.sentiment.polarity

    nt["dopamine"] += goals_sentiment * 0.04
    nt["serotonin"] += goals_sentiment * 0.02
    nt["cortisol"] += -stressors_sentiment * 0.05
    nt["GABA"] += stressors_sentiment * 0.03

    for k in nt:
        nt[k] = round(min(1, max(0, nt[k])), 2)

    if goals_sentiment is not None:
        nt["dopamine"] += goals_sentiment * 0.04  
        nt["serotonin"] += goals_sentiment * 0.02

    if stressors_sentiment is not None:
        nt["cortisol"] += stressors_sentiment * 0.05
        nt["GABA"] -= stressors_sentiment * 0.03

    memory_sentiment = TextBlob(data.childhood_scent).sentiment.polarity
    nt["serotonin"] += memory_sentiment * 0.02
    nt["hippocampus_memory_boost"] = round(memory_sentiment * 0.02, 3)
    memory_scent_profile = extract_memory_scent_profile(data.childhood_scent, fragrance_db, scent_map)
    
    # Clamp to [0, 1]
    for k in nt:
        nt[k] = round(min(1, max(0, nt[k])), 2)
    nt, region, work_env, style_score, alignment = apply_cultural_modifiers(nt, data.email, data.name)

    job_title_lower = data.job_title.lower()
    if "manager" in job_title_lower:
        nt["cortisol"] += 0.05

    if "analyst" in job_title_lower or "developer" in job_title_lower:
        nt["dopamine"] += 0.04

    if "intern" in job_title_lower or "student" in job_title_lower:
        nt["serotonin"] -= 0.02

    if "founder" in job_title_lower or "executive" in job_title_lower:
        nt["dopamine"] += 0.05
        nt["cortisol"] += 0.05
    
    if work_env == "corporate":
        nt["cortisol"] = min(1, nt.get("cortisol", 0.5) + 0.05)
        nt["dopamine"] = max(0, nt.get("dopamine", 0.5) - 0.02)

    elif work_env == "academic":
        nt["serotonin"] = min(1, nt.get("serotonin", 0.5) + 0.05)

    elif work_env == "general_consumer":
        nt["oxytocin"] = min(1, nt.get("oxytocin", 0.5) + 0.02)

    if style_score < 0:
        nt["GABA"] = max(0, nt.get("GABA", 0.5) - 0.05)
        nt["dopamine"] = min(1, nt.get("dopamine", 0.5) + 0.05)

    else:
        nt["GABA"] = min(1, nt.get("GABA", 0.5) + 0.05)

    if alignment:
        nt["oxytocin"] = min(1, nt.get("oxytocin", 0.5) + 0.03)

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

    timestamp = datetime.utcnow().isoformat()

    try:
        circadian_window, circadian_note = analyze_circadian_rhythm(nt, timestamp)
    except Exception as e:
        print(f"⚠️ Error analyzing circadian rhythm: {e}")
        circadian_window = "unknown"
        circadian_note = ["Circadian rhythm data unavailable."]

    output = {
        "name": data.name,
        "gender": gender,
        "life_stage": life_stage,
        "neurotransmitters": nt,
        "brain_regions": brain_regions,
        "subvectors": subvectors,
        "timestamp": timestamp,
        "circadian_window": circadian_window,
        "circadian_note": circadian_note,
        "reflection_tags": [data.job_title, data.productivity_limiters, data.scent_note],
        "xbox_game": xbox_game,
        "game_mode": game_mode,
        "vector_id": len(load_metadata()) - 1,
        "duration_minutes": duration_minutes,
        "switch_time": switch_time,
        "spotify_playlist": spotify_playlist,
        "age_range": age_range,
        "region": region,
        "work_env": work_env,
        "email_style_score": style_score,
        "name_email_aligned": alignment,
        "industry": industry,
        "memory_scent_profile": memory_scent_profile,
        "scent_profile": scent_profile,
        "scent_reinforcement": scent_reinforcement,
        "stressor_categories": classified_stressors,
        "olfactory_region_modeling": {
            "region": region,
            "favored_scents": cultural_affinities.get(region, [])
        
        }
        }

    required_keys = ["neurotransmitters", "xbox_game", "game_mode", "duration_minutes", "switch_time", "spotify_playlist"]
    for key in required_keys:
        if key not in output:
            raise ValueError(f"[BUG] Missing key in generate_twin_vector output: {key}")

    print("✅ FINAL OUTPUT from generate_twin_vector:", output)
    output["cognitive_focus"] = determine_cognitive_focus(subvectors)




    log_journal_entry(data, output)
    return output
