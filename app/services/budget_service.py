from fastapi import HTTPException


def optimize_budget(
    destination,
    total_budget,
    travelers=1,
    trip_days=1,
    preferred_transport="flight",
    hotel_category="3-star"
):

    if total_budget <= 0:
        raise HTTPException(status_code=400, detail="Invalid budget")

    if travelers <= 0:
        raise HTTPException(status_code=400, detail="Invalid travelers")

    if trip_days <= 0:
        raise HTTPException(status_code=400, detail="Invalid trip days")

    MIN_BUDGET_PER_PERSON_PER_DAY = 1000
    min_budget = travelers * trip_days * MIN_BUDGET_PER_PERSON_PER_DAY

    if total_budget < min_budget:
        return {
            "error": "Budget too low to plan trip",
            "minimum_recommended_budget": min_budget,
            "given_budget": total_budget,
            "trip_days": trip_days,
            "travelers": travelers,
            "suggestion": "Increase budget or reduce trip days"
        }

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
        allocation["misc"] -= 0.05

    if hotel_category.lower() == "budget":
        allocation["hotel"] -= 0.10
        allocation["activities"] += 0.05
        allocation["misc"] += 0.05
    elif hotel_category.lower() == "5-star":
        allocation["hotel"] += 0.15
        allocation["activities"] -= 0.10
        allocation["misc"] -= 0.05

    if preferred_transport == "flight":
        allocation["transport"] += 0.10
        allocation["hotel"] -= 0.05
        allocation["misc"] -= 0.05
    elif preferred_transport in ["bus", "train"]:
        allocation["transport"] -= 0.10
        allocation["hotel"] += 0.05
        allocation["activities"] += 0.05

    budget_allocation = {
        key: round(total_budget * value)
        for key, value in allocation.items()
    }

    if total_budget < 20000:
        hotel_type = "budget hotel / hostel"
        transport_type = "bus/train"
    elif total_budget < 60000:
        hotel_type = "3-star hotel"
        transport_type = preferred_transport
    else:
        hotel_type = "4 or 5-star hotel"
        transport_type = "flight"

    return {
        "destination": destination,
        "recommended_hotel": hotel_type,
        "recommended_transport": transport_type,
        "budget_allocation": budget_allocation,
        "per_person_budget": round(total_budget / travelers),
        "trip_days": trip_days,
        "travelers": travelers
    }