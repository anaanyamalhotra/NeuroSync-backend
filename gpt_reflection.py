
import openai
import os

def get_gpt_reflection(prompt: str) -> str:
    openai.api_key = os.getenv("OPENAI_API_KEY")  # Set this in your environment

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a thoughtful mental wellness assistant."},
                {"role": "user", "content": f"Reflect on this mood profile and suggest why the user might be feeling this way: {prompt}"}
            ],
            max_tokens=150
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Reflection service error: {str(e)}"
