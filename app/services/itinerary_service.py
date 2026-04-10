import re
from datetime import datetime
from typing import Dict, Optional

from app.services.groq_llm_service import ask_groq_llm


# =========================================================
# ITINERARY PARSER
# =========================================================

def _parse_itinerary(llm_text: str, total_days: int, destination: str) -> Dict:
    """
    Parse the LLM's free-text response into a structured
    { "day_1": { "morning": ..., "afternoon": ..., "evening": ... }, ... }
    """
    itinerary = {}

    for day in range(1, total_days + 1):
        # Capture everything from "Day N" up to "Day N+1" or end of string
        day_pattern = (
            rf"Day\s+{day}\s*[:\-]?\s*(.*?)"
            rf"(?=Day\s+{day + 1}\s*[:\-]|\Z)"
        )
        day_match = re.search(day_pattern, llm_text, re.DOTALL | re.IGNORECASE)

        morning = afternoon = evening = ""

        if day_match:
            block = day_match.group(1).strip()

            m = re.search(
                r"Morning\s*[:\-]\s*(.*?)(?=Afternoon\s*[:\-]|Evening\s*[:\-]|\Z)",
                block, re.DOTALL | re.IGNORECASE
            )
            a = re.search(
                r"Afternoon\s*[:\-]\s*(.*?)(?=Evening\s*[:\-]|\Z)",
                block, re.DOTALL | re.IGNORECASE
            )
            e = re.search(
                r"Evening\s*[:\-]\s*(.*?)$",
                block, re.DOTALL | re.IGNORECASE
            )

            morning   = m.group(1).strip() if m else ""
            afternoon = a.group(1).strip() if a else ""
            evening   = e.group(1).strip() if e else ""

        itinerary[f"day_{day}"] = {
            "morning":   morning   or f"Explore top attractions in {destination}",
            "afternoon": afternoon or f"Enjoy local cuisine and sightseeing in {destination}",
            "evening":   evening   or f"Relax and explore local markets in {destination}",
        }

    return itinerary


# =========================================================
# BUDGET BREAKDOWN
# =========================================================

def _budget_breakdown(
    budget: float,
    total_days: int,
    transport: str,
    hotel_type: str
) -> Dict:
    """
    Distribute total budget across hotel / transport / food / misc.
    Ratios adjust based on transport mode and hotel tier.
    """
    transport_ratio = 0.30 if transport in ("flight", "train") else 0.15
    hotel_ratio     = (
        0.40 if "5-star" in hotel_type or "luxury" in hotel_type else
        0.30 if "3-star" in hotel_type else
        0.20
    )
    food_ratio = 0.20
    misc_ratio = round(1.0 - transport_ratio - hotel_ratio - food_ratio, 2)

    hotel_total     = round(budget * hotel_ratio)
    transport_total = round(budget * transport_ratio)
    food_total      = round(budget * food_ratio)
    misc_total      = round(budget * misc_ratio)

    return {
        "hotel_per_night": round(hotel_total / max(total_days, 1)),
        "hotel_total":     hotel_total,
        "transport":       transport_total,
        "food":            food_total,
        "misc":            misc_total,
        "grand_total":     hotel_total + transport_total + food_total + misc_total,
    }


# =========================================================
# MAIN GENERATOR
# =========================================================

def generate_itinerary(
    source: str,
    destination: str,
    start_date: str,
    end_date: str,
    budget: float,
    travelers: int,
    destination_context: str = "",
    preferences: Optional[Dict] = None
):
    """
    Generate a personalized day-by-day itinerary via Groq LLM.

    Args:
        preferences: dict with keys —
            trip_type, transport, hotel_type, food_preference,
            climate, budget_min, budget_max
    """
    start      = datetime.strptime(start_date, "%Y-%m-%d")
    end        = datetime.strptime(end_date,   "%Y-%m-%d")
    total_days = (end - start).days + 1

    # ── Unpack preferences (with safe defaults) ──────────────────────────────
    prefs      = preferences or {}
    trip_type  = prefs.get("trip_type",       "leisure")
    transport  = prefs.get("transport",        "flight")
    hotel_type = prefs.get("hotel_type",       "3-star")
    food_pref  = prefs.get("food_preference",  "vegetarian")
    climate    = prefs.get("climate",          "any")
    budget_min = prefs.get("budget_min",       round(budget * 0.8))
    budget_max = prefs.get("budget_max",       budget)

    context_section = (
        destination_context.strip()
        if destination_context
        else f"Provide general travel information about {destination}."
    )

    # ── Build the LLM prompt ─────────────────────────────────────────────────
    prompt = f"""You are an expert travel planner. Create a detailed, day-by-day trip itinerary.

TRIP DETAILS:
- Source: {source}
- Destination: {destination}
- Dates: {start_date} to {end_date} ({total_days} days)
- Travelers: {travelers}
- Total Budget: INR {int(budget):,}  (range: INR {int(budget_min):,} – INR {int(budget_max):,})

USER PREFERENCES:
- Trip Type: {trip_type}
- Preferred Transport: {transport}
- Hotel Type: {hotel_type}
- Food Preference: {food_pref}
- Climate Preference: {climate}

DESTINATION KNOWLEDGE BASE:
{context_section}

PLANNING RULES:
1. Each day must have UNIQUE activities — do not repeat the same place across days.
2. Use specific attraction names, local restaurant names, and landmark names from the knowledge base above.
3. Tailor the plan to a "{trip_type}" trip style.
4. Suggest {food_pref} food options and local restaurants for {destination}.
5. Day 1 morning should account for travel/arrival from {source} via {transport}.
6. Day {total_days} evening should account for checkout and departure.
7. Keep the budget within INR {int(budget):,} for {travelers} traveler(s).

Respond using EXACTLY this format — no preamble, no extra text:

Day 1:
Morning: [detailed activity]
Afternoon: [detailed activity]
Evening: [detailed activity]

Day 2:
Morning: [detailed activity]
Afternoon: [detailed activity]
Evening: [detailed activity]

(repeat for all {total_days} days)"""

    llm_text  = ask_groq_llm(prompt)

    # ── Parse LLM output into structured dict ────────────────────────────────
    itinerary = _parse_itinerary(llm_text, total_days, destination)

    # ── Build recommendations from actual preferences ─────────────────────────
    breakdown = _budget_breakdown(budget, total_days, transport, hotel_type)

    recommendations = {
        "hotel":            hotel_type,
        "transport":        transport,
        "food_preference":  food_pref,
        "trip_type":        trip_type,
        "climate":          climate,
        "travelers":        travelers,
        "total_days":       total_days,
        "budget_breakdown": breakdown,
    }

    return itinerary, recommendations
