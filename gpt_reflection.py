from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import openai
import os

router = APIRouter()

# Set your OpenAI API key securely
openai.api_key = os.getenv("OPENAI_API_KEY")

class ReflectionInput(BaseModel):
    name: str
    current_emotion: str
    recent_events: str
    goals: str

@router.post("/reflect")
def reflect(input: ReflectionInput):
    try:
        prompt = f"""
        You are a supportive and insightful cognitive companion for {input.name}.
        Their current emotional state is described as: "{input.current_emotion}".
        Recently, they experienced: "{input.recent_events}".
        Their short-term goals include: "{input.goals}".

        Write a thoughtful and motivating journal entry, offering perspective and encouragement.
        """

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a reflective journaling assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        return {"journal_entry": response['choices'][0]['message']['content']}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
