import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


def ask_llm(query: str) -> str:
    """
    Basic Groq LLM call for general travel queries.
    Used as fallback when RAG does not provide relevant results.
    """

    try:

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError("GROQ_API_KEY missing")

        client = Groq(api_key=api_key)

        response = client.chat.completions.create(

            model="llama-3.3-70b-versatile",

            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a smart travel planning assistant. "
                        "Provide helpful travel planning suggestions."
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