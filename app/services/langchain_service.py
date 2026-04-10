import re
from typing import List

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from app.services.vector_store_service import semantic_search
from app.services.groq_llm_service import ask_groq_llm


# =========================================================
# ACCESS KEYWORDS
# =========================================================

ADMIN_ONLY_KEYWORDS = [
    "vendor",
    "vendor cost",
    "margin",
    "profit",
    "selling price",
    "transport vendor cost",
]

ADMIN_AGENT_KEYWORDS = [
    "supplier",
    "supplier cost",
    "supplier hotel rate",
    "hotel rate",
]

PUBLIC_PRICING_KEYWORDS = [
    "final package price",
    "package price",
    "discount offer",
    "trip price",
    "budget",
    "cost of trip",
]

PUBLIC_TRAVEL_KEYWORDS = [
    "itinerary",
    "places to visit",
    "best time",
    "popular attractions",
    "hotel",
    "destination",
    "food",
    "travel guide",
]


# =========================================================
# HELPERS
# =========================================================

def contains_keywords(query: str, keywords: List[str]) -> bool:
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in keywords)


def is_admin_only_query(query: str) -> bool:
    return contains_keywords(query, ADMIN_ONLY_KEYWORDS)


def is_admin_agent_query(query: str) -> bool:
    return contains_keywords(query, ADMIN_AGENT_KEYWORDS)


def is_internal_query(query: str) -> bool:
    return (
        is_admin_only_query(query)
        or is_admin_agent_query(query)
    )


def check_access(query: str, role: str):
    # admin → full access
    if role == "admin":
        return None

    # agent → allow supplier cost
    if role == "travel_agent":
        if is_admin_only_query(query):
            return (
                "Access denied: vendor cost and margin data "
                "are restricted to admin users only."
            )

        return None

    # user → block both admin + agent internal
    if role == "user":
        if is_internal_query(query):
            return (
                "Access denied: internal pricing and supplier "
                "data are restricted to authorized roles only."
            )

        return None

    return None


# =========================================================
# RETRIEVER
# =========================================================

class TravelRetriever(BaseRetriever):
    role: str = "user"

    def _get_relevant_documents(self, query: str) -> List[Document]:
        results = semantic_search(query, self.role)

        docs = []

        for item in results["results"]:
            docs.append(
                Document(
                    page_content=item["text"],
                    metadata=item["metadata"]
                )
            )

        return docs


# =========================================================
# ANSWER EXTRACTION
# =========================================================

def extract_relevant_answer(query: str, docs: List[Document]) -> str:
    query_lower = query.lower()

    if not docs:
        return "No relevant information found."

    full_text = "\n\n".join([doc.page_content for doc in docs])

    lines = [
        line.strip()
        for line in full_text.splitlines()
        if line.strip()
    ]

    # ALL cities
    if "all cities" in query_lower or "all" in query_lower:
        relevant_lines = [
            line for line in lines
            if any(
                keyword in line.lower()
                for keyword in [
                    "final package price",
                    "vendor cost",
                    "margin",
                    "selling price",
                    "discount offer",
                    "supplier hotel rate"
                ]
            )
        ]

        if relevant_lines:
            return "\n".join(relevant_lines)

    # vendor
    if "vendor cost" in query_lower:
        vendor_lines = [
            line for line in lines
            if "vendor cost" in line.lower()
        ]
        if vendor_lines:
            return "\n".join(vendor_lines)

    # supplier
    if "supplier" in query_lower:
        supplier_lines = [
            line for line in lines
            if "supplier" in line.lower()
        ]
        if supplier_lines:
            return "\n".join(supplier_lines)

    # margin
    if "margin" in query_lower:
        vendor_match = re.search(
            r"vendor cost:\s*inr\s*(\d+)",
            full_text.lower()
        )

        selling_match = re.search(
            r"(selling price|final package price):\s*inr\s*(\d+)",
            full_text.lower()
        )

        if vendor_match and selling_match:
            vendor = int(vendor_match.group(1))
            selling = int(selling_match.group(2))
            margin = selling - vendor

            return (
                f"Margin: INR {margin}\n"
                f"Vendor Cost: INR {vendor}\n"
                f"Selling Price: INR {selling}"
            )

    # final package price
    if "final package price" in query_lower:
        final_price_lines = [
            line for line in lines
            if "final package price" in line.lower()
        ]

        if final_price_lines:
            return "\n".join(final_price_lines)

    # city specific
    city_keywords = [
        "goa",
        "mysore",
        "chennai",
        "bangalore",
        "mumbai",
        "delhi"
    ]

    for city in city_keywords:
        if city in query_lower:
            city_lines = [
                line for line in lines
                if city in line.lower()
            ]

            if city_lines:
                return "\n".join(city_lines[:10])

    return "\n".join(lines[:10])


# =========================================================
# MAIN QUERY HANDLER
# =========================================================

def query_travel_assistant(
    query: str,
    role: str = "user"
):
    restriction = check_access(query, role)

    if restriction:
        return {
            "query": query,
            "answer": restriction,
            "source": "access_control"
        }

    retriever = TravelRetriever(role=role)
    docs = retriever.invoke(query)

    if docs:
        answer = extract_relevant_answer(query, docs)

        return {
            "query": query,
            "answer": answer,
            "source": "rag"
        }

    if is_internal_query(query):
        return {
            "query": query,
            "answer": "No internal data found in knowledge base.",
            "source": "rag"
        }

    llm_answer = ask_groq_llm(query)

    return {
        "query": query,
        "answer": llm_answer,
        "source": "groq_llm"
    }