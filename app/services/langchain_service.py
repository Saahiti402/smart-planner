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


def query_travel_assistant(query: str, role: str = "user"):
    query_lower = query.lower()

    # admin-only queries
    admin_only_keywords = [
        "margin",
        "profit",
        "vendor cost",
        "selling price",
        "internal pricing",
        "policy rules",
        "access roles"
    ]

    # admin + travel_agent queries
    operational_keywords = [
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

    # user restriction for admin-only
    if role != "admin" and any(
        keyword in query_lower
        for keyword in admin_only_keywords
    ):
        return {
            "query": query,
            "answer": (
                "This information is restricted and available "
                "only to admin users."
            )
        }

    # user restriction for admin + agent
    if role == "user" and any(
        keyword in query_lower
        for keyword in operational_keywords
    ):
        return {
            "query": query,
            "answer": (
                "This operational pricing information is restricted "
                "and not available for user access."
            )
        }

    retriever = TravelRetriever(role=role)

    docs = retriever.invoke(query)

    if not docs:
        return {
            "query": query,
            "answer": "No relevant travel information found."
        }

    context = "\n\n".join(
        [doc.page_content for doc in docs[:3]]
    )

    return {
        "query": query,
        "answer": f"Based on travel knowledge:\n{context}"
    }