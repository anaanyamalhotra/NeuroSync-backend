from fastapi import FastAPI
from generator import generate_twin_vector, TwinRequest
from gpt_reflection import router as gpt_router

app = FastAPI()

# Root check
@app.get("/")
def read_root():
    return {"message": "NeuroSync Backend is Live!"}

# POST route for twin generation
@app.post("/generate")
def generate(data: TwinRequest):
    return generate_twin_vector(data)

# GPT reflection router
app.include_router(gpt_router)
