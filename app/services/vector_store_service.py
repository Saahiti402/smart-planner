from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer

from app.services.rag_ingestion_service import load_and_chunk_documents

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

client = PersistentClient(path="chroma_db")
COLLECTION_NAME = "travel_guides"


def get_collection():
    return client.get_or_create_collection(COLLECTION_NAME)


def rebuild_vector_store():
    # delete old collection if it exists
    existing_collections = client.list_collections()
    existing_names = [c.name for c in existing_collections]

    if COLLECTION_NAME in existing_names:
        client.delete_collection(COLLECTION_NAME)

    collection = client.get_or_create_collection(COLLECTION_NAME)

    chunks = load_and_chunk_documents()

    for chunk in chunks:
        embedding = model.encode(chunk["text"]).tolist()

        collection.add(
            documents=[chunk["text"]],
            embeddings=[embedding],
            metadatas=[chunk["metadata"]],
            ids=[
                f'{chunk["metadata"]["folder"]}_'
                f'{chunk["metadata"]["source"]}_'
                f'{chunk["metadata"]["chunk_id"]}'
            ]
        )

    return {
        "message": "Vector DB rebuilt successfully",
        "total_chunks": len(chunks)
    }


def semantic_search(query: str, role: str):
    collection = get_collection()

    query_embedding = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=10
    )

    filtered_results = []

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    for doc, metadata in zip(documents, metadatas):
        allowed_roles = metadata.get("allowed_roles", [])

        # RBAC filter only
        if role not in allowed_roles:
            continue

        filtered_results.append({
            "text": doc,
            "metadata": metadata
        })

    return {
        "query": query,
        "role": role,
        "results": filtered_results
    }


def get_destination_context(destination: str, role: str = "user"):
    result = semantic_search(destination, role)

    if not result["results"]:
        return ""

    return "\n".join(
        [doc["text"] for doc in result["results"][:2]]
    )