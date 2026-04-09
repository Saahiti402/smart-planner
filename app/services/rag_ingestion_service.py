from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_and_chunk_documents():
    docs_path = Path(__file__).resolve().parents[2] / "rag_docs"

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )

    all_chunks = []

    # recursively scan all subfolders
    for file in docs_path.rglob("*.txt"):
        raw_text = file.read_text(encoding="utf-8")

        chunks = splitter.split_text(raw_text)

        for idx, chunk in enumerate(chunks):
            folder_name = file.parent.name

            # default access for public docs
            allowed_roles = ["admin", "travel_agent", "user"]

            # admin-only confidential policy docs
            if folder_name == "policies":
                allowed_roles = ["admin"]

            # admin + agent operational pricing docs
            elif folder_name == "pricing":
                allowed_roles = ["admin", "travel_agent"]

            chunk_data = {
                "text": chunk,
                "metadata": {
                    "source": file.name,
                    "folder": folder_name,
                    "chunk_id": idx,
                    "allowed_roles": allowed_roles
                }
            }

            all_chunks.append(chunk_data)

    return all_chunks