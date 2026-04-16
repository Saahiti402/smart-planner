import re

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

@traceable(
    name="route_travel_query",
    project_name="smart-travel-planner"
)
def route_travel_query(query: str, role: str = "user"):
    query_lower = query.lower()

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

    # =====================================================
    # BUDGET OPTIMIZATION TOOL
    # =====================================================
    if any(
        keyword in query_lower
        for keyword in ["budget", "optimize", "under"]
    ):
        budget_match = re.search(r"(\d+)", query_lower)

        city_match = re.findall(
            r"(goa|mysore|chennai|switzerland)",
            query_lower
        )

        budget = int(budget_match.group(1)) if budget_match else 10000
        city = city_match[0] if city_match else "goa"

        return {
            "tool_used": "budget_tool",
            "response": optimize_budget(
                destination=city,
                total_budget=budget
            )
        }

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
    if any(
        keyword in query_lower
        for keyword in [
            "itinerary",
            "plan trip",
            "trip plan",
            "3 day",
            "5 day",
            "travel plan"
        ]
    ):
        city_match = re.findall(
            r"(goa|mysore|chennai|switzerland)",
            query_lower
        )

        city = city_match[0] if city_match else "goa"

        itinerary, recommendations = generate_itinerary(
            source="Bangalore",
            destination=city,
            start_date="2026-04-15",
            end_date="2026-04-17",
            budget=15000,
            travelers=1
        )

        return {
            "tool_used": "itinerary_tool",
            "response": itinerary,
            "recommendations": recommendations
        }

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