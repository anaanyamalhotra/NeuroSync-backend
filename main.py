from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import os
import random
import requests
import openai
from generator import generate_twin_vector, infer_gender, apply_modifiers, extract_keywords
import nltk
from generator import build_scent_profile
from vector_store import add_twin
from fastapi import Query
import pandas as pd
from generator import extract_memory_scent_profile
from vector_store import load_metadata
from textblob import TextBlob
from generator import infer_life_stage_from_text


from textblob import download_corpora
nltk_data_path = os.path.join(os.path.dirname(__file__), "nltk_data")
os.environ["NLTK_DATA"] = nltk_data_path
nltk.data.path.append(nltk_data_path)
os.makedirs(nltk_data_path, exist_ok=True)

download_corpora.download_all()

required = [
    "punkt",
    "averaged_perceptron_tagger",
    "wordnet",
    "brown",
    "movie_reviews"
]

for corpus in required:
    try:
        nltk.data.find(corpus)
    except LookupError:
        nltk.download(corpus, download_dir=nltk_data_path)


# === INIT ===
openai.api_key = os.getenv("OPENAI_API_KEY")
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
    assigned_sex: Optional[str] = "unspecified"

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
def determine_cognitive_focus(subvectors):
    if not subvectors:
        return "general cognition"

    dominant_region = max(subvectors, key=lambda region: sum(subvectors[region].values()))
    focus_map = {
        "amygdala": "emotional AI",
        "hippocampus": "memory/NLP",
        "hypothalamus": "stress modeling",
        "prefrontal_cortex": "decision AI",
        "insula": "interoception AI"
    }
    return focus_map.get(dominant_region, "general cognition")


    
def get_fragrance_notes(scent):
    return fragrance_db.get(scent.lower().strip(), [])

def match_game(favorite_scent, stressors_text, neurotransmitters):
    scent = favorite_scent.lower().strip()
    stress_keywords = extract_keywords(stressors_text)

    # === Step 1: Filter games that have scent affinity ===
    candidates = [g for g in game_profiles if scent in g.get("scent_affinity", {})]
    if not candidates:
        candidates = game_profiles  # fallback to all

    # === Step 2: Score games based on scent strength and NT alignment ===
    def score_game(game):
        scent_score = game["scent_affinity"].get(scent, 0)
        nt_score = sum(neurotransmitters.get(tag, 0.5) for tag in game.get("tags", [])) / len(game.get("tags", []) or [1])
        return scent_score * 0.6 + nt_score * 0.4  # Weighted: scent more important

    candidates.sort(key=score_game, reverse=True)
    best_game = candidates[0]

    # === Step 3: Rationale for match ===
    flat_neurotransmitters = {k: v for k, v in neurotransmitters.items() if isinstance(v, (float, int))}

    dominant_nt = max(neurotransmitters, key=neurotransmitters.get)
    rationale = (
        f"Matched with '{best_game['name']}' because its scent affinity with '{scent}' "
        f"is high and it supports neurotransmitters like {', '.join(best_game['tags'])}. "
        f"Your current dominant neurotransmitter is {dominant_nt}."
    )

    return {
        "xbox_game": best_game["name"],
        "game_mode": random.choice(best_game["modes"]),
        "duration_minutes": random.randint(*best_game["duration_range"]),
        "switch_time": "After 30 mins" if "burnout" in stress_keywords else "After 20 mins",
        "spotify_playlist": best_game.get("spotify_playlist", "Focus Boost"),
        "match_reason": rationale
    }

# === API ROUTES ===
@app.post("/generate")
async def generate(data: TwinRequest):
    try:
        print("== ✅ Request received at /generate ==")
        goals_sentiment = TextBlob(data.career_goals).sentiment.polarity
        stressors_sentiment = TextBlob(data.productivity_limiters).sentiment.polarity
        twin = generate_twin_vector(data, goals_sentiment=goals_sentiment, stressors_sentiment=stressors_sentiment)
        scent_profile = build_scent_profile(data.scent_note)
        memory_scent_profile = extract_memory_scent_profile(data.childhood_scent, fragrance_db, scent_map)
        print(f"📊 Sentiment — Goals: {goals_sentiment}, Stressors: {stressors_sentiment}")

        twin["goals_sentiment"] = goals_sentiment
        twin["stressors_sentiment"] = stressors_sentiment
        if goals_sentiment < -0.3:
            twin["neurotransmitters"]["dopamine"] = max(0, twin["neurotransmitters"].get("dopamine", 0.5) - 0.05)
            twin["neurotransmitters"]["serotonin"] = max(0, twin["neurotransmitters"].get("serotonin", 0.5) - 0.05)
        if stressors_sentiment < -0.3:
            twin["neurotransmitters"]["cortisol"] = min(1, twin["neurotransmitters"].get("cortisol", 0.5) + 0.1)
            twin["neurotransmitters"]["GABA"] = max(0, twin["neurotransmitters"].get("GABA", 0.5) - 0.05)
       

        from vector_store import load_metadata  # already imported at the top

        

        print("DEBUG: Twin vector keys:", list(twin.keys()))

        # Defensive check
        game = match_game(data.scent_note, data.productivity_limiters, twin["neurotransmitters"])
        twin.update(game)
        twin["timestamp"] = datetime.utcnow().isoformat()

        required_keys = ["neurotransmitters", "xbox_game"]
        for key in required_keys:
            if key not in twin:
                raise ValueError(f"❌ Key '{key}' missing from twin output")

        metadata = load_metadata()

        metadata.append({
            "name": twin.get("name", "unknown"),
            "gender": twin.get("gender", "unspecified"),
            "life_stage": twin.get("life_stage", "unknown"),
            "age_range": twin.get("age_range", "unknown"),
            "timestamp": twin.get("timestamp", datetime.utcnow().isoformat()),
            "vector_id": len(load_metadata()) - 1,
            "user_id": user_id,
            "ethnicity": twin.get("ethnicity", "Uncategorized")
        })
                
        add_twin(twin)

        print("== ✅ Final Output ==", twin)

        twin["cognitive_focus"] = determine_cognitive_focus(twin.get("subvectors", {}))
        
        output = {
            "status": "success",
            "neurotransmitters": twin.get("neurotransmitters", {}),
            "xbox_game": twin.get("xbox_game", "Unknown Game"),
            "game_mode": twin.get("game_mode", "Solo"),
            "duration_minutes": twin.get("duration_minutes", 20),
            "switch_time": twin.get("switch_time", "After 20 mins"),
            "spotify_playlist": twin.get("spotify_playlist", "Focus Boost"),
            "match_reason": twin.get("match_reason", "No reason provided."),
            "cognitive_focus": twin["cognitive_focus"],
            "twin_vector": twin,
            "memory_scent_profile": memory_scent_profile,
            "timestamp": datetime.utcnow().isoformat(), 
            "brain_regions": twin.get("brain_regions", {}),
            "vector_id": vector_id,
            "goals_sentiment": twin.get("goals_sentiment", 0),
            "stressors_sentiment": twin.get("stressors_sentiment", 0),
            "subvectors": twin.get("subvectors", {}),
            "scent_reinforcement": twin.get("scent_reinforcement", "lavender"),
            "lowest_region": twin.get("lowest_region", ""),
            "scent_profile": scent_profile,
        }
        print("== ✅ Final Output ==", output)
        return JSONResponse(content=json.loads(json.dumps(output, default=str)))
    

    except Exception as e:
        print("❌ ERROR in /generate:", str(e))
        raise HTTPException(status_code=500, detail=f"Internal Error: {e}")
        # Explicit status to help Streamlit know this is an error
        
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
            work_env = data.neurotransmitters.get("work_env", "general_consumer")
            style_score = data.neurotransmitters.get("email_style_score", 0)
            aligned = data.neurotransmitters.get("name_email_aligned", False)

            if work_env == "corporate":
                tone = "Focus on work-life balance and actionable calm-down strategies. Assume the user may be under pressure."

            elif work_env == "academic":
                tone = "Emphasize structure, routine, and intellectual grounding. Recommend curiosity-fueled recovery strategies."

            else:
                tone = "Keep the tone empathetic and casual — support emotional regulation and creative rejuvenation."

            if style_score < 0:
                tone += " Keep it light and encouraging — possibly a younger or expressive user."

            elif aligned:
                tone += " You can assume the user is self-aware and identity-aligned. Reinforce motivation gently."

            game_reco = f"Today’s game: {data.xbox_game} ({data.game_mode}), play for ~{data.duration_minutes} minutes, then switch: {data.switch_time}."
            playlist = f"We’ve also curated a Spotify playlist for today: {data.name}'s {data.game_mode} Vibes 🎶"
            return (
                f"My name is {data.name}. I feel {data.current_emotion}. "
                f"Recent events include: {data.recent_events}. My goals are: {data.goals}. "
                f"Based on my brain chemistry, here's what's going on: {joined_insights}. "
                f"{game_reco} Suggest a daily routine, calming scent and a Spotify playlist to help.\n\n"
                f"🎯 Context: {tone}"
            )

        prompt = build_prompt()

        # Call GPT
        res = openai.ChatCompletion.create(
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

        journal = res.choices[0].message.content.strip()

        if not journal:
            raise ValueError("GPT returned empty response")

        return {"journal_entry": journal}

    except Exception as e:
        print("❌ GPT fallback triggered due to:", e)
        return {"journal_entry": local_fallback()}

@app.get("/twins")
def get_twins(
    gender: Optional[str] = Query(None),
    life_stage: Optional[str] = Query(None),
    age_range: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    limit: Optional[int] = Query(None)
):
    try:
        metadata = load_metadata()

        results = [
            m for m in metadata
            if (not gender or m.get("gender") == gender)
            and (not life_stage or m.get("life_stage") == life_stage)
            and (not age_range or m.get("age_range") == age_range)
            and (not user_id or m.get("user_id") == user_id)
        ]

        # Defensive timestamp fallback
        for r in results:
            if "timestamp" not in r:
                r["timestamp"] = "unknown"

        if limit:
            results = results[:limit]

        return JSONResponse(content={"status": "success", "count": len(results), "twins": results})
    except Exception as e:
        print("❌ ERROR in /twins:", str(e))
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})
