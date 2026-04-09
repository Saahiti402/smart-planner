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
# 👤 USER 4: KEYWORDS (CONFIG SECTION)
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
