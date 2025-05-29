
# 🧠 Cogniscent Backend (FastAPI)

This is the core backend of the Cognitive Twin Intelligence Platform. It maps user-reported inputs into a neuroprofile, performs neurotransmitter modulation, recommends games/music, and triggers mood-aware UX states.

## 🔗 Endpoints

- `POST /generate` - Generates a cognitive twin JSON profile.
- `POST /reflect` - (Optional) Uses GPT to provide a reflection on the user's emotional state.

## 📦 Requirements

- fastapi
- uvicorn
- pydantic
- textblob
- requests
- tldextract
- numpy
- psycopg2
- openai (for GPT reflection)

## 🛠️ Setup

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Set your OpenAI key:
```bash
export OPENAI_API_KEY=your-api-key
```

## 🔧 File Structure

- `main.py` — FastAPI routes
- `gpt_reflection.py` — GPT-4 reflection logic
- `fragrance_notes.json` — maps perfume names to scent notes
