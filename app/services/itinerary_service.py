from datetime import datetime


def generate_itinerary(
    source,
    destination,
    start_date,
    end_date,
    budget,
    travelers,
    destination_context=""
):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    total_days = (end - start).days + 1

    itinerary = {}

    context_hint = (
        destination_context[:300]
        if destination_context
        else f"Explore popular attractions in {destination}"
    )

    for day in range(1, total_days + 1):
        itinerary[f"day_{day}"] = {
            "morning": context_hint,
            "afternoon": (
                f"Enjoy local cuisine and sightseeing in {destination}"
            ),
            "evening": (
                f"Relax and explore nightlife / shopping in {destination}"
            )
        }

    estimated_hotel = budget * 0.4
    estimated_transport = budget * 0.3
    estimated_food = budget * 0.2
    misc = budget * 0.1

    recommendations = {
        "hotel": "3-star hotel",
        "transport": "flight",
        "budget_breakdown": {
            "hotel": estimated_hotel,
            "transport": estimated_transport,
            "food": estimated_food,
            "misc": misc
        }
    }

    return itinerary, recommendations