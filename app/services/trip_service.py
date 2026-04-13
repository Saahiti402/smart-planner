from datetime import date, datetime
import uuid
from sqlalchemy.orm import Session
from app.models import Trip



def classify_trip(trip):
    today = date.today()

    if trip.end_date < today:
        return "past"
    elif trip.start_date > today:
        return "planned"   
    else:
        return "ongoing"



def create_trip(db: Session, data: dict):
    trip = Trip(
        id=uuid.uuid4(),
        user_id=uuid.UUID(data["user_id"]),
        source_location=data["source"],
        destination=data["destination"],
        start_date=datetime.strptime(data["start_date"], "%Y-%m-%d").date(), 
        end_date=datetime.strptime(data["end_date"], "%Y-%m-%d").date(),      
        budget=data["budget"],
        travelers_count=data["travelers"],
        status="planned"
    )

    db.add(trip)
    db.commit()
    db.refresh(trip)

    return trip



def get_all_trips(db: Session, user_id: str):
    trips = db.query(Trip).filter(
        Trip.user_id == uuid.UUID(user_id)
    ).all()

    result = []

    for trip in trips:
        result.append({
            "trip_id": str(trip.id),
            "destination": trip.destination,
            "status": classify_trip(trip),   
            "budget": trip.budget,
            "start_date": str(trip.start_date),
            "end_date": str(trip.end_date)
        })

    return result


# ==========================
# NATURAL LANGUAGE QUERY
# ==========================
def query_user_trips(db: Session, user_id: str, query: str):
    query = query.lower()

    trips = db.query(Trip).filter(
        Trip.user_id == uuid.UUID(user_id)
    ).all()

    if not trips:
        return {"answer": "No trips found"}

    past, ongoing, planned = [], [], []

    for trip in trips:
        category = classify_trip(trip)

        if category == "past":
            past.append(trip)
        elif category == "ongoing":
            ongoing.append(trip)
        else:
            planned.append(trip)

    # --------------------------
    # QUERY CASES
    # --------------------------

    # 1. Past trips
    if "past" in query:
        return {
            "answer": "Here are your past trips",
            "data": [
                {
                    "destination": t.destination,
                    "budget": t.budget,
                    "dates": f"{t.start_date} to {t.end_date}"
                } for t in past
            ]
        }

    # 2. Current trip
    if "current" in query or "status" in query:
        if ongoing:
            t = ongoing[0]
            return {
                "answer": f"Your current trip is to {t.destination}",
                "status": "ongoing",
                "start_date": str(t.start_date),
                "end_date": str(t.end_date),
                "budget": t.budget
            }
        return {"answer": "No ongoing trips"}

    # 3. Last trip to a city (example: Goa)
    for trip in sorted(trips, key=lambda x: x.start_date, reverse=True):
        if trip.destination.lower() in query:
            return {
                "answer": f"Last trip to {trip.destination}",
                "budget": trip.budget,
                "start_date": str(trip.start_date),
                "end_date": str(trip.end_date)
            }

    # 4. Planned trips (UPDATED)
    if "planned" in query or "next" in query:
        return {
            "answer": "Your planned trips",
            "data": [
                {
                    "destination": t.destination,
                    "start_date": str(t.start_date)
                } for t in planned
            ]
        }

    return {"answer": "Sorry, I couldn't understand your query"}