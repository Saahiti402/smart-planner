from datetime import date, datetime
import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models import Trip


def classify_trip(trip):
    today = date.today()

    # highest priority → explicit completed status
    if trip.status and trip.status.lower() == "completed":
        return "past"

    # fallback date logic
    if trip.end_date < today:
        return "past"
    elif trip.start_date > today:
        return "planned"
    else:
        return "ongoing"


def create_trip(db: Session, data: dict):

    required_fields = ["user_id", "source", "destination", "start_date", "end_date", "budget", "travelers"]

    for field in required_fields:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"{field} is required")

    try:
        user_id = uuid.UUID(data["user_id"])
    except:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    try:
        start_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
    except:
        raise HTTPException(status_code=400, detail="Invalid date format")

    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Invalid date range")

    if data["budget"] <= 0:
        raise HTTPException(status_code=400, detail="Invalid budget")

    if data["travelers"] <= 0:
        raise HTTPException(status_code=400, detail="Invalid travelers count")

    trip = Trip(
        id=uuid.uuid4(),
        user_id=user_id,
        source_location=data["source"],
        destination=data["destination"],
        start_date=start_date,
        end_date=end_date,
        budget=data["budget"],
        travelers_count=data["travelers"],
        status="planned"
    )

    db.add(trip)
    db.commit()
    db.refresh(trip)

    return trip


def get_all_trips(db: Session, user_id: str):

    try:
        user_uuid = uuid.UUID(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    trips = db.query(Trip).filter(
        Trip.user_id == user_uuid
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


def query_user_trips(db: Session, user_id: str, query: str):

    query = query.lower()

    try:
        user_uuid = uuid.UUID(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    trips = db.query(Trip).filter(
        Trip.user_id == user_uuid
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

    for trip in sorted(trips, key=lambda x: x.start_date, reverse=True):
        if trip.destination.lower() in query:
            return {
                "answer": f"Last trip to {trip.destination}",
                "budget": trip.budget,
                "start_date": str(trip.start_date),
                "end_date": str(trip.end_date)
            }

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

def mark_latest_trip_completed(db: Session, user_id: str):
    latest_trip = db.query(Trip).filter(
        Trip.user_id == uuid.UUID(user_id)
    ).order_by(
        Trip.start_date.desc()
    ).first()

    if not latest_trip:
        return {"answer": "No trips found"}

    latest_trip.status = "completed"
    db.commit()

    return {
        "answer": (
            f"Your latest trip to "
            f"{latest_trip.destination} "
            f"has been marked as completed."
        ),
        "destination": latest_trip.destination,
        "status": latest_trip.status
    }

def get_latest_trip(db: Session, user_id: str):
    latest_trip = db.query(Trip).filter(
        Trip.user_id == uuid.UUID(user_id)
    ).order_by(
        Trip.start_date.desc()
    ).first()

    if not latest_trip:
        return {"answer": "No trips found"}

    return {
        "destination": latest_trip.destination,
        "status": latest_trip.status,
        "budget": latest_trip.budget,
        "start_date": str(latest_trip.start_date),
        "end_date": str(latest_trip.end_date)
    }

