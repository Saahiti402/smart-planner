from pathlib import Path


DESTINATIONS_FILE = (
    Path(__file__).resolve().parents[2]
    / "rag_docs"
    / "destinations"
    / "destinations_detailed.txt"
)
PRICING_FILE = (
    Path(__file__).resolve().parents[2]
    / "rag_docs"
    / "pricing"
    / "pricing_detailed.txt"
)
HOTELS_FILE = (
    Path(__file__).resolve().parents[2]
    / "rag_docs"
    / "hotels"
    / "hotels_detailed.txt"
)


SECTION_HEADERS = {
    "Overview:": "overview",
    "Best Time to Visit:": "best_time",
    "Popular Attractions:": "popular_attractions",
    "Suggested Itinerary:": "suggested_itinerary",
    "Food Recommendations:": "food_recommendations",
}


def _parse_destinations() -> list[dict]:
    if not DESTINATIONS_FILE.exists():
        return []

    destinations = []
    current = None
    current_section = None

    for raw_line in DESTINATIONS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("=== CITY:") and line.endswith("==="):
            if current:
                destinations.append(current)

            city_name = line.replace("=== CITY:", "").replace("===", "").strip().title()
            current = {
                "name": city_name,
                "slug": city_name.lower().replace(" ", "-"),
                "overview": "",
                "best_time": "",
                "popular_attractions": [],
                "suggested_itinerary": [],
                "food_recommendations": [],
            }
            current_section = None
            continue

        if current is None:
            continue

        if line in SECTION_HEADERS:
            current_section = SECTION_HEADERS[line]
            continue

        if current_section in {"popular_attractions", "suggested_itinerary", "food_recommendations"}:
            current[current_section].append(line.lstrip("- ").strip())
        elif current_section:
            current[current_section] = line

    if current:
        destinations.append(current)

    return destinations


def _parse_city_blocks(file_path: Path) -> dict[str, list[str]]:
    if not file_path.exists():
        return {}

    parsed = {}
    current_city = None
    current_lines = []

    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("=== CITY:") and line.endswith("==="):
            if current_city:
                parsed[current_city] = current_lines

            current_city = line.replace("=== CITY:", "").replace("===", "").strip().title()
            current_lines = []
            continue

        if current_city:
            current_lines.append(line)

    if current_city:
        parsed[current_city] = current_lines

    return parsed


def _extract_pricing(city_name: str) -> dict:
    city_blocks = _parse_city_blocks(PRICING_FILE)
    lines = city_blocks.get(city_name, [])

    public_pricing = []
    current_section = None

    for line in lines:
        if line == "Public Pricing:":
            current_section = "public"
            continue
        if line == "Internal Pricing (ADMIN ONLY):":
            current_section = "internal"
            continue

        cleaned = line.lstrip("- ").strip()
        if current_section == "public":
            public_pricing.append(cleaned)

    return {
        "public_pricing": public_pricing,
    }


def _extract_hotel_pricing(city_name: str) -> dict:
    city_blocks = _parse_city_blocks(HOTELS_FILE)
    lines = city_blocks.get(city_name, [])

    hotels = []
    for line in lines:
        if line == "Hotels:" or line.startswith("Check-in:") or line.startswith("Check-out:"):
            continue
        hotels.append(line.lstrip("- ").strip())

    return {
        "hotel_options": hotels,
    }


def list_destinations() -> list[dict]:
    listed = []
    for destination in _parse_destinations():
        pricing = _extract_pricing(destination["name"])
        listed.append(
            {
                "name": destination["name"],
                "slug": destination["slug"],
                "best_time": destination["best_time"],
                "top_attractions_preview": destination["popular_attractions"][:3],
                "price_preview": pricing["public_pricing"][0] if pricing["public_pricing"] else "",
            }
        )

    return listed


def compare_destinations(destinations: list[str]) -> dict:
    available = _parse_destinations()
    lookup = {}
    for destination in available:
        enriched = {
            **destination,
            **_extract_pricing(destination["name"]),
            **_extract_hotel_pricing(destination["name"]),
        }
        lookup[destination["name"].lower()] = enriched
        lookup[destination["slug"].lower()] = enriched

    found = []
    missing = []

    for requested in destinations:
        match = lookup.get(requested.strip().lower())
        if match:
            found.append(match)
        else:
            missing.append(requested)

    return {
        "requested": destinations,
        "found": found,
        "missing": missing,
        "total_available": len(available),
    }
