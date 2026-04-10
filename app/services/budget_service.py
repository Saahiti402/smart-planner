def optimize_budget(
    total_budget,
    travelers=1,
    trip_days=1,
    preferred_transport="flight",
    hotel_category="3-star"
):
    """
    Suggest optimal allocation of travel budget based on constraints.

    Logic:
    - Adjust allocations depending on trip length
    - Scale per-person cost
    - Suggest economical alternatives when budget is tight
    """

    # Base allocation ratios
    allocation = {
        "hotel": 0.35,
        "transport": 0.30,
        "food": 0.20,
        "activities": 0.10,
        "misc": 0.05
    }

    # Adjust based on trip duration
    if trip_days <= 2:
        allocation["transport"] += 0.05
        allocation["hotel"] -= 0.05
    elif trip_days >= 7:
        allocation["activities"] += 0.05
        allocation["misc"] += 0.05
        allocation["transport"] -= 0.05
        allocation["hotel"] -= 0.05

    # Budget per traveler
    per_person_budget = total_budget / travelers

    # Transport suggestion logic
    if per_person_budget < 15000:
        transport = "train / bus"
    elif preferred_transport == "flight":
        transport = "economy flight"
    else:
        transport = preferred_transport

    # Hotel suggestion logic
    if per_person_budget < 12000:
        hotel = "budget hotel / hostel"
    elif per_person_budget < 25000:
        hotel = "3-star hotel"
    else:
        hotel = hotel_category

    # Compute optimized allocation
    optimized_budget = {
        key: round(total_budget * value, 2)
        for key, value in allocation.items()
    }

    # Final recommendation object
    recommendation = {
        "recommended_transport": transport,
        "recommended_hotel": hotel,
        "budget_allocation": optimized_budget,
        "per_person_budget": round(per_person_budget, 2),
        "trip_days": trip_days,
        "travelers": travelers
    }

    return recommendation