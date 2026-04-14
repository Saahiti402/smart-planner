import uuid
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.services.budget_service import optimize_budget
from app.services.groq_llm_service import ask_groq_llm as ask_llm
from app.services.trip_service import (
    create_trip,
    get_all_trips,
    query_user_trips, 
    mark_latest_trip_completed, 
    get_latest_trip
)


load_dotenv()

from app.database import engine, Base, get_db
from app.models import (
    User,
    Trip,
    Itinerary,
    UserPreference,
    Conversation
)
from app.schemas import (
    UserRegisterSchema,
    UserLoginSchema,
    TripPlanSchema,
    UserPreferenceSchema,
    DestinationCompareSchema,
)
from app.auth import hash_password, verify_password
from app.services.rag_ingestion_service import load_and_chunk_documents
from app.services.vector_store_service import (
    semantic_search,
    rebuild_vector_store
)
from app.services.agent_service import travel_planning_agent
from app.services.langchain_service import query_travel_assistant
from app.services.external_travel_service import _fetch_weather_data, _fetch_activities_data, _fetch_flights_data
from typing import Optional
from pydantic import BaseModel
from app.services.ask_travel_router import route_travel_query

class ExternalTravelToolRequest(BaseModel):
    type: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    date: Optional[str] = None
    return_date: Optional[str] = None
    city: Optional[str] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None

app = FastAPI(title="Smart Travel Planner Backend")

@app.post("/tools/external-travel")
def external_travel_tool(request: ExternalTravelToolRequest):
    if request.type == "weather":
        if not request.city:
            return {"error": "Missing 'city' for weather. Example: {'type': 'weather', 'city': 'Goa'}"}
        return {"type": "weather", "data": _fetch_weather_data(request.city)}
        
    elif request.type == "places":
        if not request.city:
            return {"error": "Missing 'city' for places. Example: {'type': 'places', 'city': 'Goa'}"}
        from app.services.external_travel_service import _fetch_activities_data
        return {"type": "places", "data": _fetch_activities_data(request.city)}
        
    elif request.type == "flights":
        if not request.origin or not request.destination or not request.date:
            return {
                "error": "Missing 'origin', 'destination', or 'date' for flights. "
                         "Example: {'type': 'flights', 'origin': 'Bangalore', 'destination': 'Delhi', 'date': '2025-06-15'}"
            }
        return {
            "type": "flights", 
            "data": _fetch_flights_data(request.origin, request.destination, request.date, request.return_date)
        }
        
    elif request.type == "hotels":
        if not request.city or not request.check_in or not request.check_out:
            return {
                "error": "Missing 'city', 'check_in', or 'check_out' for hotels. "
                         "Example: {'type': 'hotels', 'city': 'Goa', 'check_in': '2026-10-10', 'check_out': '2026-10-15'}"
            }
        from app.services.external_travel_service import _fetch_hotels_data
        return {
            "type": "hotels",
            "data": _fetch_hotels_data(request.city, request.check_in, request.check_out)
        }
        
    return {"error": "Invalid payload type."}

# ---------------- CORS FIX ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # allow all origins for local testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def home():
    return {"message": "Smart Travel Planner backend is running"}


# ---------------- USER AUTH ----------------

@app.post("/register")
def register_user(
    user_data: UserRegisterSchema,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        User.email == user_data.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=user_data.role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "user_id": str(new_user.id),
        "email": new_user.email,
        "role": new_user.role
    }


@app.post("/login")
def login_user(
    user_data: UserLoginSchema,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == user_data.email
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if not verify_password(
        user_data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid password"
        )

    return {
        "message": "Login successful",
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role
    }


# ---------------- TRIP PLANNING ----------------

@app.post("/plan-trip")
def plan_trip(
    trip_data: TripPlanSchema,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == uuid.UUID(trip_data.user_id)
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    new_trip = Trip(
        user_id=uuid.UUID(trip_data.user_id),
        source_location=trip_data.source_location,
        destination=trip_data.destination,
        start_date=datetime.strptime(
            trip_data.start_date,
            "%Y-%m-%d"
        ).date(),
        end_date=datetime.strptime(
            trip_data.end_date,
            "%Y-%m-%d"
        ).date(),
        budget=trip_data.budget,
        travelers_count=trip_data.travelers_count,
        status="planned"
    )

    db.add(new_trip)
    db.commit()
    db.refresh(new_trip)

    generated_itinerary, recommendations, decision_log = (
        travel_planning_agent(trip_data)
    )

    itinerary = Itinerary(
        trip_id=new_trip.id,
        day_plan=generated_itinerary,
        estimated_cost=trip_data.budget,
        recommendations=recommendations,
        generated_by_agent=True
    )

    db.add(itinerary)
    db.commit()

    return {
        "message": "Trip planned successfully",
        "trip_id": str(new_trip.id),
        "destination": trip_data.destination,
        "itinerary": generated_itinerary,
        "recommendations": recommendations,
        "agent_decision": decision_log
    }


# ---------------- RAG ----------------

@app.get("/test-rag-chunks")
def test_rag_chunks():
    chunks = load_and_chunk_documents()

    return {
        "total_chunks": len(chunks),
        "sample_chunk": chunks[:2]
    }


@app.post("/store-rag")
def store_rag():
    return rebuild_vector_store()


@app.get("/search-rag")
def search_rag(query: str, role: str):
    return semantic_search(query, role)


@app.get("/destinations")
def get_destinations():
    from app.services.destination_compare_service import list_destinations

    return {"destinations": list_destinations()}


@app.post("/compare-destinations")
def compare_destination_options(compare_request: DestinationCompareSchema):
    from app.services.destination_compare_service import compare_destinations

    return compare_destinations(compare_request.destinations)


# ---------------- USER PREFERENCES ----------------

@app.post("/save-preferences")
def save_preferences(
    preference_data: UserPreferenceSchema,
    db: Session = Depends(get_db)
):
    existing_pref = db.query(UserPreference).filter(
        UserPreference.user_id == uuid.UUID(
            preference_data.user_id
        )
    ).first()

    if existing_pref:
        existing_pref.budget_min = preference_data.budget_min
        existing_pref.budget_max = preference_data.budget_max
        existing_pref.preferred_transport = (
            preference_data.preferred_transport
        )
        existing_pref.preferred_hotel_type = (
            preference_data.preferred_hotel_type
        )
        existing_pref.preferred_trip_type = (
            preference_data.preferred_trip_type
        )
        existing_pref.food_preference = (
            preference_data.food_preference
        )
        existing_pref.preferred_climate = (
            preference_data.preferred_climate
        )
        existing_pref.updated_at = datetime.utcnow()

        db.commit()

        return {
            "message": "Preferences updated successfully"
        }

    new_pref = UserPreference(
        user_id=uuid.UUID(preference_data.user_id),
        budget_min=preference_data.budget_min,
        budget_max=preference_data.budget_max,
        preferred_transport=preference_data.preferred_transport,
        preferred_hotel_type=preference_data.preferred_hotel_type,
        preferred_trip_type=preference_data.preferred_trip_type,
        food_preference=preference_data.food_preference,
        preferred_climate=preference_data.preferred_climate
    )

    db.add(new_pref)
    db.commit()

    return {
        "message": "Preferences saved successfully"
    }


@app.get("/my-preferences/{user_id}")
def get_preferences(
    user_id: str,
    db: Session = Depends(get_db)
):
    preference = db.query(UserPreference).filter(
        UserPreference.user_id == uuid.UUID(user_id)
    ).first()

    if not preference:
        raise HTTPException(
            status_code=404,
            detail="Preferences not found"
        )

    return {
        "budget_min": preference.budget_min,
        "budget_max": preference.budget_max,
        "preferred_transport": preference.preferred_transport,
        "preferred_hotel_type": preference.preferred_hotel_type,
        "preferred_trip_type": preference.preferred_trip_type,
        "food_preference": preference.food_preference,
        "preferred_climate": preference.preferred_climate
    }


@app.get("/ask-travel")
def ask_travel(
    query: str,
    user_id: str,
    db: Session = Depends(get_db)
):
    # =====================================================
    # STEP 1: FETCH USER
    # =====================================================
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid user_id format"
        )

    user = db.query(User).filter(
        User.id == user_uuid
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    query_lower = query.lower().strip()

    # =====================================================
    # STEP 2: TRIP MANAGEMENT ACTIONS
    # =====================================================
    if any(
        phrase in query_lower
        for phrase in [
            "mark my recent planned trip as completed",
            "complete my latest trip",
            "mark last trip as done",
            "mark my recent trip as completed"
        ]
    ):
        response = mark_latest_trip_completed(
            db,
            user_id
        )
        tool_used = "trip_management"

    elif any(
        phrase in query_lower
        for phrase in [
            "show my recent trip",
            "show my latest trip",
            "recent trip",
            "latest trip"
        ]
    ):
        response = get_latest_trip(
            db,
            user_id
        )
        tool_used = "trip_management"

    elif any(
        keyword in query_lower
        for keyword in [
            "past trip",
            "past trips",
            "planned trips",
            "next trip",
            "current trip",
            "trip status"
        ]
    ):
        response = query_user_trips(
            db,
            user_id,
            query
        )
        tool_used = "trip_management"

    # =====================================================
    # STEP 3: NATURAL LANGUAGE TRIP PLANNING + SAVE TO DB
    # =====================================================
    elif any(
        keyword in query_lower
        for keyword in [
            "plan trip",
            "trip plan",
            "plan 3 day",
            "plan 5 day",
            "travel plan"
        ]
    ):
        # -------- detect destination --------
        destination = "Goa"

        if "mysore" in query_lower:
            destination = "Mysore"
        elif "chennai" in query_lower:
            destination = "Chennai"

        # -------- dynamic dates --------
        today = datetime.now().date()
        start_date = today + timedelta(days=1)
        end_date = start_date + timedelta(days=2)

        # -------- create trip --------
        trip_data = {
            "user_id": str(user.id),
            "source": "Bangalore",
            "destination": destination,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "budget": 15000,
            "travelers": 1
        }

        created_trip = create_trip(
            db,
            trip_data
        )

        # -------- generate itinerary --------
        routed_response = route_travel_query(
            query=query,
            role=user.role
        )

        itinerary_text = routed_response.get(
            "response",
            routed_response
        )

        recommendations = routed_response.get(
            "recommendations",
            []
        )

        # -------- save itinerary --------
        itinerary_record = Itinerary(
            trip_id=created_trip.id,
            day_plan=str(itinerary_text),
            estimated_cost=created_trip.budget,
            recommendations=str(recommendations),
            generated_by_agent=True
        )

        db.add(itinerary_record)
        db.commit()

        response = {
            "trip_id": str(created_trip.id),
            "destination": created_trip.destination,
            "status": created_trip.status,
            "start_date": str(created_trip.start_date),
            "end_date": str(created_trip.end_date),
            "itinerary": itinerary_text,
            "recommendations": recommendations
        }

        tool_used = "trip_planning"

    # =====================================================
    # STEP 4: ALL OTHER NATURAL LANGUAGE QUERIES
    # =====================================================
    else:
        routed_response = route_travel_query(
            query=query,
            role=user.role
        )

        response = routed_response.get(
            "response",
            routed_response
        )

        tool_used = routed_response.get(
            "tool_used",
            "travel_assistant"
        )

    # =====================================================
    # STEP 5: SAVE CONVERSATION
    # =====================================================
    conversation = Conversation(
        user_id=user.id,
        user_message=query,
        assistant_response=str(response),
        tool_used=tool_used
    )

    db.add(conversation)
    db.commit()

    # =====================================================
    # STEP 6: RETURN RESPONSE
    # =====================================================
    return {
        "user_role": user.role,
        "tool_used": tool_used,
        "response": response
    }
# Budget Optimization with Structured Input
@app.post("/optimize-budget")
def optimize_budget_api(data: dict):

    result = optimize_budget(
        destination=data["destination"],
        total_budget=data["budget"],
        travelers=data.get("travelers", 1),
        trip_days=data.get("trip_days", 1),
        preferred_transport=data.get("preferred_transport", "flight"),
        hotel_category=data.get("hotel_category", "3-star")
    )

    return result


# Budget Optimization with Natural Language Input
@app.post("/optimize-budget-nl")
def optimize_budget_natural_language(query: dict):

    user_text = query["query"]

    prompt = f"""
Extract travel details from text.

Return ONLY JSON.

Format:
{{
 "destination": "",
 "budget": 0,
 "travelers": 0,
 "trip_days": 0
}}

Text:
{user_text}
"""

    structured_data = ask_llm(prompt)

    import json, re

    json_match = re.search(r"\{.*\}", structured_data, re.DOTALL)

    if not json_match:
        raise ValueError("No JSON returned from LLM")

    parsed = json.loads(json_match.group())

    result = optimize_budget(
        destination=parsed["destination"],
        total_budget=parsed["budget"],
        travelers=parsed["travelers"],
        trip_days=parsed["trip_days"]
    )

    return result

#trip service
@app.post("/trip")
def add_trip(data: dict, db: Session = Depends(get_db)):
    trip = create_trip(db, data)

    return {
        "message": "Trip created successfully",
        "trip_id": str(trip.id)
    }


@app.get("/trips/{user_id}")
def fetch_trips(user_id: str, db: Session = Depends(get_db)):
    return get_all_trips(db, user_id)


@app.post("/trip/query")
def query_trips(data: dict, db: Session = Depends(get_db)):
    return query_user_trips(
        db,
        data["user_id"],
        data["query"]
    )

@app.get("/conversations")
def get_conversations(
    user_id: str,
    db: Session = Depends(get_db)
):
    conversations = db.query(Conversation).filter(
        Conversation.user_id == uuid.UUID(user_id)
    ).order_by(
        Conversation.created_at.desc()
    ).all()

    return {
        "total_conversations": len(conversations),
        "conversations": [
            {
                "id": str(c.id),
                "user_message": c.user_message,
                "assistant_response": c.assistant_response,
                "tool_used": c.tool_used,
                "created_at": c.created_at.isoformat()
            }
            for c in conversations
        ]
    }