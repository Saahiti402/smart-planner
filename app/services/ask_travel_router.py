import re
from datetime import date, timedelta

from app.services.langchain_service import query_travel_assistant
from app.services.destination_compare_service import compare_destinations
from app.services.budget_service import optimize_budget
from app.services.external_travel_service import external_travel_tool
from app.services.itinerary_service import generate_itinerary
from app.services.trip_service import (
    query_user_trips,
    get_latest_trip,
    mark_latest_trip_completed
)
from langsmith.run_helpers import traceable

SUPPORTED_DESTINATIONS = (
    "goa",
    "mysore",
    "chennai",
    "switzerland",
    "delhi",
    "mumbai",
)

SUPPORTED_TRANSPORTS = (
    "flight",
    "train",
    "bus",
    "car",
)

BUDGET_QUERY_HINTS = (
    "budget",
    "optimize",
    "under",
    "within",
    "afford",
    "allocation",
)

TRIP_MANAGEMENT_PATTERNS = (
    r"\bmy trips?\b",
    r"\bshow (?:me )?(?:my )?trips?\b",
    r"\bpast trips?\b",
    r"\bcurrent trips?\b",
    r"\bplanned trips?\b",
    r"\btrip status\b",
    r"\bstatus of (?:my )?trip\b",
)

HOTEL_CATEGORY_PATTERNS = (
    (r"\b5[- ]?star\b", "5-star"),
    (r"\b4[- ]?star\b", "4-star"),
    (r"\b3[- ]?star\b", "3-star"),
    (r"\bluxury\b", "luxury"),
    (r"\bbudget\s+(?:hotel|stay|accommodation)\b", "budget"),
    (r"\bhostel\b", "budget"),
)


def extract_destination_from_query(
    query_lower: str,
    default: str = "goa"
) -> str:
    city_match = re.search(
        rf"\b({'|'.join(SUPPORTED_DESTINATIONS)})\b",
        query_lower
    )
    return city_match.group(1) if city_match else default


def extract_trip_days(
    query_lower: str,
    default: int = 3
) -> int:
    day_patterns = [
        r"\b(\d+)\s*[- ]?day(?:s)?\b",
        r"\bday(?:s)?\D{0,3}(\d+)\b",
    ]

    for pattern in day_patterns:
        day_match = re.search(pattern, query_lower)
        if day_match:
            return max(int(day_match.group(1)), 1)

    return default


def _parse_money_amount(
    number_text: str,
    suffix: str | None = None
) -> int:
    amount = float(number_text.replace(",", ""))
    suffix_lower = (suffix or "").lower()

    if suffix_lower == "k":
        amount *= 1_000
    elif suffix_lower in {"lakh", "lac"}:
        amount *= 100_000

    return int(round(amount))


def extract_budget_amount(query_lower: str) -> int | None:
    keyword_patterns = [
        r"(?:under|within|around|about|budget(?:\s+is|\s+of)?|max(?:imum)?(?:\s+budget)?(?:\s+of)?)(?:\s+is)?\s*(?:₹|rs\.?|inr)?\s*(\d[\d,]*(?:\.\d+)?)\s*(k|lakh|lac)?",
        r"(?:₹|rs\.?|inr)\s*(\d[\d,]*(?:\.\d+)?)\s*(k|lakh|lac)?",
    ]

    for pattern in keyword_patterns:
        match = re.search(pattern, query_lower, re.IGNORECASE)
        if match:
            return _parse_money_amount(
                match.group(1),
                match.group(2)
            )

    candidates = []
    for match in re.finditer(
        r"(?:₹|rs\.?|inr)?\s*(\d[\d,]*(?:\.\d+)?)\s*(k|lakh|lac)?",
        query_lower,
        re.IGNORECASE
    ):
        amount = _parse_money_amount(
            match.group(1),
            match.group(2)
        )
        if amount >= 1_000:
            candidates.append(amount)

    if candidates:
        return max(candidates)

    return None


def extract_travelers(
    query_lower: str,
    default: int = 1
) -> int:
    traveler_patterns = [
        r"\bfor\s+(\d+)\s+(?:people|persons|traveller|travellers|traveler|travelers|adult|adults)\b",
        r"\b(\d+)\s+(?:people|persons|traveller|travellers|traveler|travelers|adult|adults|pax)\b",
        r"\b(?:traveller|travellers|traveler|travelers)\D{0,3}(\d+)\b",
    ]

    for pattern in traveler_patterns:
        match = re.search(pattern, query_lower, re.IGNORECASE)
        if match:
            return max(int(match.group(1)), 1)

    if "solo" in query_lower:
        return 1

    if "couple" in query_lower:
        return 2

    return default


def extract_transport(
    query_lower: str,
    default: str = "flight"
) -> str:
    for transport in SUPPORTED_TRANSPORTS:
        if re.search(rf"\b{transport}\b", query_lower):
            return transport

    return default


def extract_hotel_category(
    query_lower: str,
    default: str = "3-star"
) -> str:
    for pattern, hotel_category in HOTEL_CATEGORY_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return hotel_category

    return default


def is_itinerary_query(query: str) -> bool:
    query_lower = query.lower().strip()

    if any(
        keyword in query_lower
        for keyword in [
            "itinerary",
            "trip plan",
            "travel plan",
        ]
    ):
        return True

    return bool(
        re.search(r"\bplan\b.*\btrip\b", query_lower)
        or re.search(r"\b\d+\s*[- ]?day(?:s)?\s+trip\b", query_lower)
        or "day trip" in query_lower
    )


def is_budget_query(query: str) -> bool:
    query_lower = query.lower().strip()

    if not any(keyword in query_lower for keyword in BUDGET_QUERY_HINTS):
        return False

    return bool(
        re.search(r"\boptimi[sz]e\b.*\bbudget\b", query_lower)
        or re.search(r"\bbudget\b.*\boptimi[sz]e\b", query_lower)
        or re.search(r"\bbudget\b.*\btrip\b", query_lower)
        or re.search(r"\bunder\b\s*(?:₹|rs\.?|inr)?\s*[\d,]+", query_lower)
        or re.search(r"\bwithin\b\s*(?:₹|rs\.?|inr)?\s*[\d,]+", query_lower)
        or "budget allocation" in query_lower
    )


def is_trip_management_query(query: str) -> bool:
    query_lower = query.lower().strip()

    return any(
        re.search(pattern, query_lower)
        for pattern in TRIP_MANAGEMENT_PATTERNS
    )

@traceable(
    name="route_travel_query",
    project_name="smart-travel-planner"
)
def route_travel_query(
    query: str,
    role: str = "user",
    destination: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    trip_days: int | None = None,
    preferences: dict | None = None
):
    query_lower = query.lower().strip()
    force_itinerary = any(
        value is not None
        for value in [destination, start_date, end_date, trip_days]
    )
    preferences = preferences or {}

    def build_itinerary_response():
        city = destination or extract_destination_from_query(
            query_lower,
            default="goa"
        )
        total_days = (
            max(trip_days, 1)
            if trip_days is not None
            else extract_trip_days(query_lower)
        )

        itinerary_start_date = start_date
        itinerary_end_date = end_date

        if not itinerary_start_date or not itinerary_end_date:
            itinerary_start = date.today() + timedelta(days=1)
            itinerary_end = itinerary_start + timedelta(
                days=max(total_days - 1, 0)
            )
            itinerary_start_date = itinerary_start.strftime("%Y-%m-%d")
            itinerary_end_date = itinerary_end.strftime("%Y-%m-%d")

        itinerary_preferences = {
            "trip_type": preferences.get("preferred_trip_type"),
            "transport": preferences.get("preferred_transport"),
            "hotel_type": preferences.get("preferred_hotel_type"),
            "food_preference": preferences.get("food_preference"),
            "climate": preferences.get("preferred_climate"),
            "budget_min": preferences.get("budget_min"),
            "budget_max": preferences.get("budget_max"),
        }
        itinerary_preferences = {
            key: value
            for key, value in itinerary_preferences.items()
            if value not in (None, "")
        }

        itinerary, recommendations = generate_itinerary(
            source="Bangalore",
            destination=city.title(),
            start_date=itinerary_start_date,
            end_date=itinerary_end_date,
            budget=15000,
            travelers=1,
            preferences=itinerary_preferences or None
        )

        return {
            "tool_used": "itinerary_tool",
            "response": itinerary,
            "recommendations": recommendations
        }

    def build_budget_response():
        city = destination or extract_destination_from_query(
            query_lower,
            default="goa"
        )
        total_budget = extract_budget_amount(query_lower)
        budget_source = "query"

        if total_budget is None:
            total_budget = (
                preferences.get("budget_max")
                or preferences.get("budget_min")
            )
            if total_budget is not None:
                budget_source = "saved_preferences"

        if total_budget is None:
            return {
                "tool_used": "budget_tool",
                "response": {
                    "error": (
                        "Please mention your total budget in the chat "
                        "or save a budget preference first."
                    ),
                    "example": (
                        "Try: optimize my Goa budget for 2 people "
                        "for 3 days under 30000 by train"
                    )
                }
            }

        total_days = (
            max(trip_days, 1)
            if trip_days is not None
            else extract_trip_days(query_lower, default=3)
        )
        travelers_count = extract_travelers(
            query_lower,
            default=1
        )
        preferred_transport = extract_transport(
            query_lower,
            default=preferences.get("preferred_transport") or "flight"
        )
        hotel_category = extract_hotel_category(
            query_lower,
            default=preferences.get("preferred_hotel_type") or "3-star"
        )

        result = optimize_budget(
            destination=city.title(),
            total_budget=total_budget,
            travelers=travelers_count,
            trip_days=total_days,
            preferred_transport=preferred_transport,
            hotel_category=hotel_category
        )
        result["budget_source"] = budget_source
        result["inputs_used"] = {
            "destination": city.title(),
            "budget": total_budget,
            "trip_days": total_days,
            "travelers": travelers_count,
            "preferred_transport": preferred_transport,
            "hotel_category": hotel_category,
        }

        return {
            "tool_used": "budget_tool",
            "response": result
        }

    # =====================================================
    # DESTINATION COMPARISON TOOL
    # =====================================================
    if "compare" in query_lower:
        cities = re.findall(
            r"(goa|mysore|chennai|switzerland|delhi|mumbai)",
            query_lower
        )

        if len(cities) >= 2:
            return {
                "tool_used": "comparison_tool",
                "response": compare_destinations(cities)
            }

<<<<<<< HEAD
    if force_itinerary and is_itinerary_query(query):
        return build_itinerary_response()

    # =====================================================
    # BUDGET OPTIMIZATION TOOL
    # =====================================================
    if is_budget_query(query):
        return build_budget_response()

=======
       # =====================================================
    # BUDGET OPTIMIZATION TOOL (NATURAL LANGUAGE)
    # =====================================================
    if any(word in query_lower for word in ["budget", "cost", "cheap", "under", "price"]):

        # -------- extract budget --------
        budget_match = re.search(r'\d{4,7}', query_lower)
        total_budget = int(budget_match.group()) if budget_match else 15000

        # -------- extract destination --------
        city_match = re.findall(
            r"(goa|mysore|chennai|switzerland|mumbai|delhi)",
            query_lower
        )
        destination = city_match[0] if city_match else "goa"

        # -------- extract trip days --------
        days_match = re.search(r'(\d+)\s*day', query_lower)
        trip_days = int(days_match.group(1)) if days_match else 3

        # -------- extract travelers --------
        travelers_match = re.search(
            r'(\d+)\s*(people|person|traveler|members)',
            query_lower
        )
        travelers = int(travelers_match.group(1)) if travelers_match else 1

        # -------- transport --------
        if "flight" in query_lower:
            preferred_transport = "flight"
        elif "train" in query_lower:
            preferred_transport = "train"
        elif "bus" in query_lower:
            preferred_transport = "bus"
        else:
            preferred_transport = "flight"

        # -------- hotel category --------
        if "5 star" in query_lower or "luxury" in query_lower:
            hotel_category = "5-star"

        elif "budget hotel" in query_lower or "cheap hotel" in query_lower:
            hotel_category = "budget"

        else:
            hotel_category = "3-star"

        return {
            "tool_used": "budget_tool",
            "response": optimize_budget(
                destination=destination,
                total_budget=total_budget,
                travelers=travelers,
                trip_days=trip_days,
                preferred_transport=preferred_transport,
                hotel_category=hotel_category
            )
        }
>>>>>>> 4e472495b315bf9f55b21dc8d4ad57492e15c278
    # =====================================================
    # EXTERNAL TRAVEL TOOL
    # =====================================================
    if (
        any(
        keyword in query_lower
        for keyword in [
            "weather",
            "temperature",
            "rain",
            "forecast",
            "flight",
            "fly",
            "airline",
            "hotel",
            "stay",
            "accommodation",
            "activity",
            "attraction",
            "things to do",
            "places"
        ]
    )
    and "supplier" not in query_lower
    and "vendor" not in query_lower
    and "margin" not in query_lower
    ):
        return {
            "tool_used": "external_travel_tool",
            "response": external_travel_tool.invoke(query)
        }

    # =====================================================
    # ITINERARY TOOL
    # =====================================================
    if is_itinerary_query(query):
        return build_itinerary_response()

    # =====================================================
    # DEFAULT → RAG + LLM FALLBACK
    # =====================================================
    return {
        "tool_used": "rag_tool",
        "response": query_travel_assistant(
            query=query,
            role=role
        )
    }

def route_trip_query(query: str, db, user_id: str):
    query_lower = query.lower()

    if (
        ("mark" in query_lower or "complete" in query_lower)
        and "trip" in query_lower
        and any(word in query_lower for word in ["completed", "done", "finished"])
    ):
        return {
            "tool_used": "trip_management",
            "response": mark_latest_trip_completed(db, user_id)
        }

    if "latest" in query_lower or "recent" in query_lower:
        return {
            "tool_used": "trip_management",
            "response": get_latest_trip(db, user_id)
        }

    if "trip" in query_lower:
        return {
            "tool_used": "trip_management",
            "response": query_user_trips(db, user_id, query)
        }

    return None
