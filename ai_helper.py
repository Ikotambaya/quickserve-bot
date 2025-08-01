import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()  # Uses OPENAI_API_KEY from environment

def get_ai_recommendation(user_input):
    prompt = f"""You are a friendly food assistant in Nigeria. 
A customer says: "{user_input}"
Suggest Nigerian food dishes they might enjoy in a friendly tone."""

    response = client.chat.completions.create(
        model="gpt-4o",  # If you really want "gpt-4o-mini", update accordingly
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.8,
    )

    recommendation = response.choices[0].message.content.strip()
    return recommendation
