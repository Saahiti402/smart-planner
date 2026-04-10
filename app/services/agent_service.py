import uuid

from app.services.itinerary_service import generate_itinerary
from app.services.vector_store_service import get_destination_context
from app.database import SessionLocal
from app.models import UserPreference


def travel_planning_agent(trip_data):
    """
    Full trip planning pipeline:

    1. Load saved user preferences from DB (hotel, transport, food, etc.)
    2. Fetch destination context from ChromaDB RAG (attractions, itinerary, food)
    3. Pass both to generate_itinerary() which calls Groq LLM
       to produce a real, personalised day-by-day itinerary.
    """
    db = SessionLocal()

    try:
        # ── Step 1: Load saved preferences ───────────────────────────────────
        preference = db.query(UserPreference).filter(
            UserPreference.user_id == uuid.UUID(trip_data.user_id)
        ).first()

        role = getattr(trip_data, "role", "user")

        preferences = {}
        if preference:
            preferences = {
                "trip_type":       preference.preferred_trip_type,
                "transport":       preference.preferred_transport,
                "hotel_type":      preference.preferred_hotel_type,
                "food_preference": preference.food_preference,
                "climate":         preference.preferred_climate,
                "budget_min":      preference.budget_min,
                "budget_max":      preference.budget_max,
            }

        # ── Step 2: Fetch destination RAG context ─────────────────────────────
        destination_context = get_destination_context(
            trip_data.destination,
            role=role
        )

        # ── Step 3: Generate itinerary via LLM + preferences ─────────────────
        itinerary, recommendations = generate_itinerary(
            source=trip_data.source_location,
            destination=trip_data.destination,
            start_date=trip_data.start_date,
            end_date=trip_data.end_date,
            budget=trip_data.budget,
            travelers=trip_data.travelers_count,
            destination_context=destination_context,
            preferences=preferences
        )

        # ── Step 4: Decision log for transparency ─────────────────────────────
        pref_summary = (
            f"trip_type={preferences.get('trip_type')}, "
            f"transport={preferences.get('transport')}, "
            f"hotel={preferences.get('hotel_type')}, "
            f"food={preferences.get('food_preference')}"
            if preferences
            else "no saved preferences — used defaults"
        )

        decision_log = {
            "selected_tool": "rag + saved_preferences + groq_llm",
            "destination":   trip_data.destination,
            "role":          role,
            "preferences_used": pref_summary,
            "rag_context_found": bool(destination_context),
            "reason": (
                f"RAG context retrieved for {trip_data.destination}. "
                f"User preferences loaded from DB. "
                f"Groq LLM generated a personalised {preferences.get('trip_type', 'leisure')} "
                f"itinerary tailored to {preferences.get('transport', 'flight')} travel, "
                f"{preferences.get('hotel_type', '3-star')} hotel, "
                f"and {preferences.get('food_preference', 'vegetarian')} food."
            )
        }

        return itinerary, recommendations, decision_log

    finally:
        db.close()
