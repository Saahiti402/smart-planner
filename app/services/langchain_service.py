from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from typing import List

from app.services.vector_store_service import semantic_search


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
# ACCESS CONTROL KEYWORDS
# =========================================================

ADMIN_ONLY_KEYWORDS = [
    "margin",
    "profit",
    "vendor cost",
    "selling price",
    "internal pricing",
    "policy rules",
    "access roles"
]

OPERATIONAL_KEYWORDS = [
    "supplier discount",
    "supplier discounts",
    "vendor rate",
    "vendor rates",
    "negotiated rate",
    "negotiated rates",
    "discount percentage",
    "hotel partner cost",
    "supplier pricing",
    "package pricing"
]


# =========================================================
# ACCESS CONTROL LOGIC
# =========================================================

def check_access(query: str, role: str):
    query_lower = query.lower()

    # admin-only restriction
    if role != "admin" and any(
        keyword in query_lower
        for keyword in ADMIN_ONLY_KEYWORDS
    ):
        return (
            "This information is restricted and available "
            "only to admin users."
        )

    # admin + agent restriction
    if role == "user" and any(
        keyword in query_lower
        for keyword in OPERATIONAL_KEYWORDS
    ):
        return (
            "This operational pricing information is restricted "
            "and not available for user access."
        )

    return None


# =========================================================
# MAIN QUERY HANDLER
# =========================================================

def query_travel_assistant(
    query: str,
    role: str = "user"
):
    # Step 1: Access Control
    restriction = check_access(query, role)

    if restriction:
        return {
            "query": query,
            "answer": restriction
        }

    # Step 2: Retrieve relevant docs
    retriever = TravelRetriever(role=role)
    docs = retriever.invoke(query)

    if not docs:
        return {
            "query": query,
            "answer": "No relevant travel information found."
        }

    # Step 3: Build response context
    context = "\n\n".join(
        [doc.page_content for doc in docs[:3]]
    )

    # Step 4: Return final response
    return {
        "query": query,
        "answer": f"Based on travel knowledge:\n{context}"
    }