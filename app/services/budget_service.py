from fastapi import HTTPException
from langsmith.run_helpers import traceable


@traceable(
    name="optimize_budget",
    project_name="smart-travel-planner"
)
def optimize_budget(
    destination: str,
    total_budget: float,
    travelers: int,
    trip_days: int,
    preferred_transport: str,
    hotel_category: str
):

    validate_budget_inputs(total_budget, travelers, trip_days)

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

    allocation = calculate_allocation(
        total_budget,
        trip_days,
        preferred_transport,
        hotel_category
    )

    budget_allocation = {
        key: round(total_budget * value)
        for key, value in allocation.items()
    }

    hotel_type, transport_type = recommend_categories(
        total_budget,
        preferred_transport
    )

    return {
        "destination": destination,
        "recommended_hotel": hotel_type,
        "recommended_transport": transport_type,
        "budget_allocation": budget_allocation,
        "per_person_budget": round(total_budget / travelers),
        "trip_days": trip_days,
        "travelers": travelers
    }


@traceable(
    name="validate_budget_inputs",
    project_name="smart-travel-planner"
)
def validate_budget_inputs(total_budget, travelers, trip_days):

    if total_budget <= 0:
        raise HTTPException(status_code=400, detail="Invalid budget")

    if travelers <= 0:
        raise HTTPException(status_code=400, detail="Invalid travelers")

    if trip_days <= 0:
        raise HTTPException(status_code=400, detail="Invalid trip days")


@traceable(
    name="calculate_budget_allocation",
    project_name="smart-travel-planner"
)
def calculate_allocation(
    total_budget,
    trip_days,
    preferred_transport,
    hotel_category
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

    return allocation


@traceable(
    name="budget_category_recommendation",
    project_name="smart-travel-planner"
)
def recommend_categories(total_budget, preferred_transport):

    if total_budget < 20000:
        return "budget hotel / hostel", "bus/train"

    elif total_budget < 60000:
        return "3-star hotel", preferred_transport

    else:
        return "4 or 5-star hotel", "flight"