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


def ask_groq_llm_with_context(query: str, context: str) -> str:
    """Call Groq LLM with RAG context. Uses context if relevant,
    falls back to general knowledge otherwise."""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a smart travel planning assistant. "
                        "You have access to a travel knowledge base provided below. "
                        "Use the context if it is relevant to the question. "
                        "If the context is not relevant to the question, "
                        "answer from your general travel knowledge. "
                        "Always give clear, helpful, and accurate travel advice."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Knowledge Base Context:\n{context}\n\n"
                        f"Question: {query}"
                    )
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