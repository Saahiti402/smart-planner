import uuid

from app.services.itinerary_service import generate_itinerary
from app.services.vector_store_service import get_destination_context
from app.database import SessionLocal
from app.models import UserPreference


def travel_planning_agent(trip_data):
    db = SessionLocal()

    try:
        preference = db.query(UserPreference).filter(
            UserPreference.user_id == uuid.UUID(trip_data.user_id)
        ).first()

        # use actual role from request
        role = getattr(trip_data, "role", "user")

        destination_context = get_destination_context(
            trip_data.destination,
            role=role
        )

        preference_hint = ""

        if preference:
            preference_hint = (
                f"Trip style: {preference.preferred_trip_type}, "
                f"Transport: {preference.preferred_transport}, "
                f"Hotel: {preference.preferred_hotel_type}, "
                f"Food: {preference.food_preference}"
            )

        full_context = (
            destination_context + "\n" + preference_hint
        )

        itinerary, recommendations = generate_itinerary(
            trip_data.source_location,
            trip_data.destination,
            trip_data.start_date,
            trip_data.end_date,
            trip_data.budget,
            trip_data.travelers_count,
            full_context
        )

        decision_log = {
            "selected_tool": "rag + memory + itinerary_service",
            "reason": (
                f"Used destination guide + saved preferences "
                f"for {trip_data.destination} "
                f"with role {role}"
            )
        }

        return itinerary, recommendations, decision_log

    finally:
        db.close()