import os
import openai
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

def get_ai_recommendation(user_input):
    prompt = f"""You are a friendly food assistant in Nigeria. 
A customer says: "{user_input}"
Suggest Nigerian food dishes they might enjoy in a friendly tone."""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.8,
    )

    recommendation = response.choices[0].message.content.strip()
    return recommendation
