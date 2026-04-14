from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


def detect_allowed_roles(text: str):
    text_lower = text.lower()

    has_internal = any(
        keyword in text_lower
        for keyword in [
            "vendor cost",
            "supplier hotel rate",
            "transport vendor cost",
            "margin",
            "profit",
            "selling price"
        ]
    )

    has_public = any(
        keyword in text_lower
        for keyword in [
            "final package price",
            "discount offer",
            "3 day trip price",
            "public pricing"
        ]
    )

    # mixed chunk → allow all roles
    if has_internal and has_public:
        return ["admin", "travel_agent", "user"]

    # only internal → restrict
    if has_internal:
        return ["admin"]

    # public chunk
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


def read_pdf_text(file_path: Path):
    """
    Extract text from PDF file
    """
    text = ""
    reader = PdfReader(str(file_path))

    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"

    return text


def load_and_chunk_documents():
    docs_path = Path(__file__).resolve().parents[2] / "rag_docs"

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " "]
    )

    all_chunks = []

    # Scan txt + pdf files
    supported_files = list(docs_path.rglob("*.txt")) + list(
        docs_path.rglob("*.pdf")
    )

    for file in supported_files:
        # Read file content
        if file.suffix.lower() == ".txt":
            raw_text = file.read_text(encoding="utf-8")

        elif file.suffix.lower() == ".pdf":
            raw_text = read_pdf_text(file)

        else:
            continue

        if not raw_text.strip():
            continue

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
                    "allowed_roles": allowed_roles,
                    "file_type": file.suffix.lower()
                }
            }

            all_chunks.append(chunk_data)

    return all_chunks