import re
from typing import Dict, List, Optional, Tuple

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from app.services.vector_store_service import semantic_search
from app.services.groq_llm_service import ask_groq_llm, ask_groq_llm_with_context


# =========================================================
# ACCESS CONTROL KEYWORDS
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
    "cost of trip",
]


# =========================================================
# PRICING FIELD DEFINITIONS
# =========================================================

# Ordered — more specific patterns must come before shorter overlapping ones
QUERY_TO_FIELD: List[Tuple[str, str]] = [
    ("transport vendor cost",  "transport vendor cost"),
    ("transport vendor",       "transport vendor cost"),
    ("transport cost",         "transport vendor cost"),
    ("supplier hotel rate",    "supplier hotel rate"),
    ("supplier hotel",         "supplier hotel rate"),
    ("supplier rate",          "supplier hotel rate"),
    ("supplier",               "supplier hotel rate"),
    ("vendor cost",            "vendor cost"),
    ("selling price",          "selling price"),
    ("margin",                 "margin"),
    ("profit",                 "margin"),
    ("final package price",    "final package price"),
    ("package price",          "final package price"),
    ("discount offer",         "discount offer"),
    ("discount",               "discount offer"),
    ("3 day trip price",       "3 day trip price"),
    ("trip price",             "3 day trip price"),
    ("3 day trip",             "3 day trip price"),
]

FIELD_DISPLAY: Dict[str, str] = {
    "transport vendor cost": "Transport vendor cost",
    "supplier hotel rate":   "Supplier hotel rate",
    "vendor cost":           "Vendor cost",
    "selling price":         "Selling price",
    "margin":                "Margin",
    "final package price":   "Final package price",
    "discount offer":        "Discount offer",
    "3 day trip price":      "3-day trip price",
}

# Which fields belong to public pricing vs internal pricing
PUBLIC_FIELDS  = {"final package price", "discount offer", "3 day trip price"}
INTERNAL_FIELDS = {
    "vendor cost", "selling price", "margin",
    "supplier hotel rate", "transport vendor cost",
}

# Line-level matchers for each field
# Returns True when a pricing line belongs to that field
FIELD_MATCHERS: Dict[str, callable] = {
    "transport vendor cost": lambda l: "transport vendor cost:" in l,
    "supplier hotel rate":   lambda l: "supplier hotel rate:" in l,
    "vendor cost":           lambda l: "vendor cost:" in l and "transport" not in l,
    "selling price":         lambda l: "selling price:" in l,
    "margin":                lambda l: re.match(r"[-•\s]*margin:", l) is not None,
    "final package price":   lambda l: "final package price:" in l,
    "discount offer":        lambda l: "discount offer:" in l,
    "3 day trip price":      lambda l: "3 day trip price:" in l,
}

KNOWN_CITIES = [
    "goa", "mysore", "chennai", "bangalore", "mumbai", "delhi"
]

# Pricing query keywords — used to decide RAG extraction vs Groq LLM
PRICING_QUERY_KEYWORDS = [
    "vendor cost", "vendor", "margin", "profit", "selling price",
    "transport vendor", "supplier",
    "final package price", "package price", "discount offer", "discount",
    "trip price", "3 day trip", "pricing",
]


# =========================================================
# HELPERS
# =========================================================

def contains_keywords(query: str, keywords: List[str]) -> bool:
    q = query.lower()
    return any(kw in q for kw in keywords)


def is_admin_only_query(query: str) -> bool:
    return contains_keywords(query, ADMIN_ONLY_KEYWORDS)


def is_admin_agent_query(query: str) -> bool:
    return contains_keywords(query, ADMIN_AGENT_KEYWORDS)


def is_internal_query(query: str) -> bool:
    return is_admin_only_query(query) or is_admin_agent_query(query)


def is_pricing_query(query: str) -> bool:
    return contains_keywords(query, PRICING_QUERY_KEYWORDS + PUBLIC_PRICING_KEYWORDS)


def get_mentioned_city(query_lower: str) -> Optional[str]:
    for city in KNOWN_CITIES:
        if city in query_lower:
            return city
    return None


def detect_pricing_field(query_lower: str) -> Optional[str]:
    """Return the canonical pricing field name the query is asking about."""
    for keyword, field in QUERY_TO_FIELD:
        if keyword in query_lower:
            return field
    return None


def format_inr(amount: int) -> str:
    return f"INR {amount:,}"


def extract_inr_from_line(line: str) -> Optional[int]:
    """Pull the numeric INR value out of a pricing line."""
    match = re.search(r"inr\s*([\d,]+)", line.lower())
    if match:
        return int(match.group(1).replace(",", ""))
    return None


def check_access(query: str, role: str) -> Optional[str]:
    if role == "admin":
        return None

    if role == "travel_agent":
        if is_admin_only_query(query):
            return (
                "Access denied: vendor cost and margin data "
                "are restricted to admin users only."
            )
        return None

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
# STRUCTURED PRICING EXTRACTION
# =========================================================

def parse_city_pricing(docs: List[Document]) -> Dict[str, Dict[str, int]]:
    """
    Build a per-city pricing dictionary from retrieved docs.

    Strategy:
      1. Combine all doc text and split on  === CITY: <name> ===  headers.
         This works even when multiple cities land in the same chunk and
         the metadata city tag is wrong (always the first city found).
      2. Fall back to metadata-based parsing for any city still missing.
      3. Derive margin = selling_price - vendor_cost where not explicit.

    Returns:
        {
            "goa":    {"vendor cost": 14000, "margin": 4500, ...},
            "mysore": {"vendor cost": 9000,  "margin": 3000, ...},
            ...
        }
    """
    city_data: Dict[str, Dict[str, int]] = {}

    # ── Pass 1: parse city-section headers from the raw text ─────────────────
    combined = "\n".join(doc.page_content for doc in docs)

    # Split on  === CITY: GOA ===  (case-insensitive)
    parts = re.split(r"===\s*city:\s*(\w+)\s*===", combined, flags=re.IGNORECASE)
    # parts = [preamble, "GOA", goa_text, "MYSORE", mysore_text, ...]

    i = 1
    while i + 1 < len(parts):
        city      = parts[i].strip().lower()
        city_text = parts[i + 1]

        if city not in city_data:
            city_data[city] = {}

        for raw_line in city_text.splitlines():
            line = raw_line.lower().strip()
            for field, matcher in FIELD_MATCHERS.items():
                if field in city_data[city]:
                    continue
                if matcher(line):
                    value = extract_inr_from_line(line)
                    if value is not None:
                        city_data[city][field] = value
        i += 2

    # ── Pass 2: metadata fallback for docs without city headers ──────────────
    for doc in docs:
        city = doc.metadata.get("city", "general")
        if city == "general" or city in city_data:
            continue
        city_data[city] = {}
        for raw_line in doc.page_content.splitlines():
            line = raw_line.lower().strip()
            for field, matcher in FIELD_MATCHERS.items():
                if field in city_data[city]:
                    continue
                if matcher(line):
                    value = extract_inr_from_line(line)
                    if value is not None:
                        city_data[city][field] = value

    # ── Pass 3: derive margin where not stored explicitly ────────────────────
    for city, data in city_data.items():
        if "margin" not in data:
            vendor  = data.get("vendor cost")
            selling = data.get("selling price")
            if vendor and selling:
                data["margin"] = selling - vendor

    return city_data


def format_city_full(city: str, data: Dict[str, int]) -> str:
    """Return a full pricing breakdown for one city, nicely formatted."""
    lines = [f"Pricing breakdown for {city.title()}:"]

    public_items = [(f, data[f]) for f in PUBLIC_FIELDS if f in data]
    if public_items:
        lines.append("  Public Pricing:")
        for field, value in public_items:
            lines.append(f"    • {FIELD_DISPLAY[field]}: {format_inr(value)}")

    internal_items = [(f, data[f]) for f in INTERNAL_FIELDS if f in data]
    if internal_items:
        lines.append("  Internal Pricing:")
        for field, value in internal_items:
            lines.append(f"    • {FIELD_DISPLAY[field]}: {format_inr(value)}")

    return "\n".join(lines)


# =========================================================
# MAIN EXTRACTION DISPATCHER
# =========================================================

def extract_relevant_answer(query: str, docs: List[Document]) -> str:
    """
    Given retrieved docs and the user query, return a clean, human-readable
    pricing answer.

    Logic:
      ① specific field + specific city   → single value answer
      ② specific field + all cities      → that field across all cities
      ③ no specific field + specific city → full breakdown for that city
      ④ no specific field + no city      → overview of all cities
    """
    if not docs:
        return "No relevant pricing information found in the knowledge base."

    query_lower       = query.lower()
    mentioned_city    = get_mentioned_city(query_lower)
    pricing_field     = detect_pricing_field(query_lower)
    city_pricing      = parse_city_pricing(docs)

    if not city_pricing:
        return "Could not extract pricing data from the knowledge base."

    # ── ① Specific field + specific city ─────────────────────────────────────
    if pricing_field and mentioned_city:
        data  = city_pricing.get(mentioned_city, {})
        value = data.get(pricing_field)
        label = FIELD_DISPLAY.get(pricing_field, pricing_field)

        if value is not None:
            # For margin, also show breakdown
            if pricing_field == "margin":
                vendor  = data.get("vendor cost")
                selling = data.get("selling price")
                result  = f"{label} for {mentioned_city.title()}: {format_inr(value)}"
                if vendor and selling:
                    result += (
                        f"\n  • Vendor cost:   {format_inr(vendor)}"
                        f"\n  • Selling price: {format_inr(selling)}"
                    )
                return result

            return f"{label} for {mentioned_city.title()}: {format_inr(value)}"

        return (
            f"No '{label}' data found for {mentioned_city.title()} "
            f"in the knowledge base."
        )

    # ── ② Specific field + all cities ────────────────────────────────────────
    if pricing_field and not mentioned_city:
        label   = FIELD_DISPLAY.get(pricing_field, pricing_field)
        results = []

        for city, data in city_pricing.items():
            value = data.get(pricing_field)
            if value is not None:
                if pricing_field == "margin":
                    vendor  = data.get("vendor cost")
                    selling = data.get("selling price")
                    detail  = (
                        f" (Vendor: {format_inr(vendor)}, "
                        f"Selling: {format_inr(selling)})"
                        if vendor and selling else ""
                    )
                    results.append(
                        f"  • {city.title()}: {format_inr(value)}{detail}"
                    )
                else:
                    results.append(
                        f"  • {city.title()}: {format_inr(value)}"
                    )

        if results:
            return f"{label} across all cities:\n" + "\n".join(results)
        return f"No '{label}' data found in the knowledge base."

    # ── ③ No field + specific city  →  full breakdown ────────────────────────
    if mentioned_city and not pricing_field:
        data = city_pricing.get(mentioned_city)
        if data:
            return format_city_full(mentioned_city, data)
        return f"No pricing data found for {mentioned_city.title()}."

    # ── ④ No field + no city  →  overview of all cities ──────────────────────
    if city_pricing:
        sections = []
        for city, data in city_pricing.items():
            sections.append(format_city_full(city, data))
        return "\n\n".join(sections)

    return "No pricing data found in the knowledge base."


# =========================================================
# MAIN QUERY HANDLER
# =========================================================

def query_travel_assistant(
    query: str,
    role: str = "user"
):
    """
    Routing logic:
      1. Access control — block forbidden queries first.
      2. Pricing queries (internal or public) → RAG extraction via
         extract_relevant_answer (structured, city-aware).
      3. All other travel queries → Groq LLM, with RAG context if available.
      4. No RAG docs → Groq LLM directly.
    """

    # ── 1. Access control ────────────────────────────────────────────────────
    restriction = check_access(query, role)
    if restriction:
        return {
            "query":  query,
            "answer": restriction,
            "source": "access_control"
        }

    retriever = TravelRetriever(role=role)
    docs      = retriever.invoke(query)

    # ── 2. Pricing queries → structured RAG extraction ────────────────────────
    if is_internal_query(query) or is_pricing_query(query):
        if docs:
            answer = extract_relevant_answer(query, docs)
        else:
            answer = "No pricing data found in the knowledge base."

        return {
            "query":  query,
            "answer": answer,
            "source": "rag"
        }

    # ── 3. Public travel queries → Groq LLM (+ optional RAG context) ─────────
    if docs:
        context = "\n\n".join([doc.page_content for doc in docs[:5]])
        answer  = ask_groq_llm_with_context(query, context)
        return {
            "query":  query,
            "answer": answer,
            "source": "rag_llm"
        }

    # ── 4. No RAG docs → Groq LLM directly ───────────────────────────────────
    answer = ask_groq_llm(query)
    return {
        "query":  query,
        "answer": answer,
        "source": "groq_llm"
    }
