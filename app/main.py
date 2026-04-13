import uuid
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.services.budget_service import optimize_budget
from app.services.groq_llm_service import ask_groq_llm as ask_llm


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
    # Step 1 → fetch user
    user = db.query(User).filter(
        User.id == uuid.UUID(user_id)
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Step 2 → route natural language query
    response = route_travel_query(
        query=query,
        role=user.role
    )

    # Step 3 → normalize response text for conversation logging
    response_text = str(response.get("response", response))

    # Step 4 → save conversation
    conversation = Conversation(
        user_id=user.id,
        user_message=query,
        assistant_response=response_text,
        tool_used=response.get(
            "tool_used",
            "travel_assistant"
        )
    )

    db.add(conversation)
    db.commit()

    # Step 5 → return final response
    return response

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

    response = []

    for convo in conversations:
        response.append({
            "id": str(convo.id),
            "session_id": str(convo.session_id),
            "user_message": convo.user_message,
            "assistant_response": convo.assistant_response,
            "tool_used": convo.tool_used,
            "created_at": convo.created_at.isoformat()
        })

    return {
        "total_conversations": len(response),
        "conversations": response
    }

# ---------------- BUDGET OPTIMIZATION ----------------
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


# ---------------- BUDGET OPTIMIZATION ----------------
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
