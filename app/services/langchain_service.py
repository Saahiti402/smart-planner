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
    restricted_keywords = [
        "margin",
        "profit",
        "vendor cost",
        "selling price",
        "internal pricing"
    ]

    if role != "admin" and any(
        keyword in query.lower()
        for keyword in restricted_keywords
    ):
        return {
            "query": query,
            "answer": (
                "This pricing or margin information is restricted "
                "and available only to admin users."
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