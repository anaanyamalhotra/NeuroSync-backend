# NeuroSync – Cognitive Twin App (Backend)

This is the FastAPI backend for the NeuroSync Cognitive Twin app. It models neurotransmitter profiles based on scent and stressor data, assigns game/music recommendations, and supports journaling via GPT. Also includes a vector store for similarity search and metadata storage.

## Features
- `/generate`: Main endpoint to create a cognitive twin from survey inputs
- `/reflect`: GPT-powered journaling and scent/music suggestions based on brain state
- `/twins`: Returns stored cognitive twins, filterable by demographics
- Uses scent-to-neurotransmitter mapping and cognitive region modeling

## Requirements
- Python 3.8+
- FastAPI, uvicorn, faiss, openai, nltk, textblob, ethnicolr

## Setup
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

## Environment
Set your OpenAI key as an environment variable:
```bash
export OPENAI_API_KEY=your-key-here
```

## Files
- `main.py`: FastAPI app with routes
- `generator.py`: Neuroscience and NLP logic
- `vector_store.py`: Handles Faiss index + metadata
- `fragrance_notes.json`: Scent-to-neurotransmitter mapping
- `game_profiles.json`: Game tagging based on brain targets
- `vector_store/metadata.json`: Stored twins
- `vector_store/faiss_index.index`: Embedding index

## Output Format
```json
{
  "dopamine": 0.71,
  "serotonin": 0.77,
  "oxytocin": 0.72,
  "xbox_game": "Journey to the Savage Planet",
  "spotify_playlist": "Focus Boost"
}
```

## Notes
- Faiss vector: `[dopamine, serotonin, oxytocin, GABA, cortisol]`
- Demographic inference uses `ethnicolr` and job title
- Journaling is supported by `/reflect`, which returns scent/music strategies and text reflections
- Metadata can be accessed via `/twins`, which supports filtering by gender, age range, life stage, and more

## Live Demo
- 🌐 Frontend App: [https://neurosync.streamlit.app](https://neurosync.streamlit.app)
- 🧠 Backend API: [https://cogniscent-backend-ygrv.onrender.com](https://cogniscent-backend-ygrv.onrender.com)
