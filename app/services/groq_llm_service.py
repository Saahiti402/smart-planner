import os
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

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
                    "content": "You are a smart travel planning assistant."
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
            "Sorry, live travel guidance is temporarily unavailable. "
            "Please try again in a moment."
            )


def ask_groq_llm_with_context(query: str, context: str) -> str:
    """Call Groq LLM with RAG context injected into the system prompt."""
    try:
        system_prompt = (
            "You are a smart travel planning assistant. "
            "Use the following travel knowledge to answer the user's question accurately.\n\n"
            f"Context:\n{context}"
        )
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": query}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content

    except Exception:
        return (
            "Sorry, live travel guidance is temporarily unavailable. "
            "Please try again in a moment."
        )
