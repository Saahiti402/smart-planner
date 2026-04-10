import os
from groq import Groq


client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


def ask_groq_llm(query: str) -> str:
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a smart travel planning assistant. "
                        "Answer travel-related questions clearly, "
                        "accurately, and helpfully."
                    )
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            temperature=0.3
        )

        return response.choices[0].message.content

    except Exception:
        return (
            "Sorry, I am unable to fetch travel guidance right now. "
            "Please try again in a moment."
        )
