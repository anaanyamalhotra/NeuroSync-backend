# Main FastAPI app

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from generator import generate_twin_vector  # modular logic file

app = FastAPI()

# Define the request model matching frontend payload
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

@app.post("/generate")
async def generate(request: TwinRequest):
    profile = generate_twin_vector(request)
    return profile

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
