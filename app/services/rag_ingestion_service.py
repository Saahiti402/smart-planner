from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter


def detect_allowed_roles(text: str):
    text_lower = text.lower()

    # strict admin-only financial/internal sections
    admin_only_keywords = [
        "internal pricing",
        "vendor cost",
        "supplier hotel rate",
        "transport vendor cost",
        "margin",
        "profit",
        "selling price",
        "admin only"
    ]

    # public + agent + admin
    public_keywords = [
        "public pricing",
        "final package price",
        "discount offer",
        "overview",
        "best time",
        "popular attractions",
        "suggested itinerary",
        "food recommendations",
        "hotels"
    ]

    if any(keyword in text_lower for keyword in admin_only_keywords):
        return ["admin"]

    if any(keyword in text_lower for keyword in public_keywords):
        return ["admin", "travel_agent", "user"]

    # safe default = public
    return ["admin", "travel_agent", "user"]


def extract_city_name(text: str):
    text_lower = text.lower()

    cities = [
        "goa",
        "mysore",
        "chennai",
        "bangalore",
        "mumbai",
        "delhi"
    ]

    for city in cities:
        if city in text_lower:
            return city

    return "general"


def load_and_chunk_documents():
    docs_path = Path(__file__).resolve().parents[2] / "rag_docs"

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=120,
        separators=["\n\n", "\n", ".", " "]
    )

    all_chunks = []

    for file in docs_path.rglob("*.txt"):
        raw_text = file.read_text(encoding="utf-8")

        chunks = splitter.split_text(raw_text)

        for idx, chunk in enumerate(chunks):
            allowed_roles = detect_allowed_roles(chunk)

            city = extract_city_name(chunk)

            chunk_data = {
                "text": chunk,
                "metadata": {
                    "source": file.name,
                    "city": city,
                    "chunk_id": idx,
                    "allowed_roles": allowed_roles
                }
            }

            all_chunks.append(chunk_data)

    return all_chunks