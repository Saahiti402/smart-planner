def optimize_budget(
    destination,
    total_budget,
    travelers=1,
    trip_days=1,
    preferred_transport="flight",
    hotel_category="3-star"
):

    allocation = {
        "hotel": 0.35,
        "transport": 0.30,
        "food": 0.20,
        "activities": 0.10,
        "misc": 0.05
    }

    if trip_days <= 2:
        allocation["transport"] += 0.05
        allocation["hotel"] -= 0.05

    elif trip_days >= 7:
        allocation["activities"] += 0.05
        allocation["misc"] += 0.05
        allocation["transport"] -= 0.05
        allocation["hotel"] -= 0.05

    per_person_budget = total_budget / travelers

    if per_person_budget < 15000:
        recommended_transport = "bus/train"
    elif preferred_transport == "flight":
        recommended_transport = "economy flight"
    else:
        recommended_transport = preferred_transport

    if per_person_budget < 10000:
        recommended_hotel = "budget hotel / hostel"
    elif per_person_budget < 25000:
        recommended_hotel = "3-star hotel"
    else:
        recommended_hotel = hotel_category

    optimized_budget = {
        key: round(total_budget * value, 2)
        for key, value in allocation.items()
    }

    return {
        "destination": destination,
        "recommended_hotel": recommended_hotel,
        "recommended_transport": recommended_transport,
        "budget_allocation": optimized_budget,
        "per_person_budget": round(per_person_budget, 2),
        "trip_days": trip_days,
        "travelers": travelers
    }
