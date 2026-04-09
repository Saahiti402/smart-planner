from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
from app.models import UserPreference
from app.schemas import UserPreferenceSchema
from app.database import engine, Base, get_db
from app.models import User, Trip, Itinerary
from app.schemas import (
    UserRegisterSchema,
    UserLoginSchema,
    TripPlanSchema
)
from app.services.itinerary_service import generate_itinerary
from app.services.rag_ingestion_service import load_and_chunk_documents
from app.services.vector_store_service import semantic_search
from app.services.agent_service import travel_planning_agent
from app.services.vector_store_service import rebuild_vector_store
from app.auth import (
    hash_password,
    verify_password,
    create_access_token
)
from app.auth import get_current_user
from app.services.langchain_service import query_travel_assistant
from app.models import Conversation

app = FastAPI(title="Smart Travel Planner Backend")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def home():
    return {"message": "Smart Travel Planner backend is running"}


@app.post("/register")
def register_user(user_data: UserRegisterSchema, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

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
        "email": new_user.email
    }


@app.post("/login")
def login_user(user_data: UserLoginSchema, db: Session = Depends(get_db)):
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

    token = create_access_token({
        "sub": str(user.id),
        "role": user.role
    })

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "role": user.role
    }


@app.post("/plan-trip")
def plan_trip(
    trip_data: TripPlanSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Ensure token user matches request user
    if current_user["sub"] != trip_data.user_id:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized trip access"
        )

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

    # RAG-powered agent call
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

@app.post("/save-preferences")
def save_preferences(
    preference_data: UserPreferenceSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Security check
    if current_user["sub"] != preference_data.user_id:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized access"
        )

    existing_pref = db.query(UserPreference).filter(
        UserPreference.user_id == uuid.UUID(preference_data.user_id)
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
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user["sub"] != user_id:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized access"
        )

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
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    role = current_user["role"]

    response = query_travel_assistant(query, role)

    conversation = Conversation(
        user_id=uuid.UUID(current_user["sub"]),
        user_message=query,
        assistant_response=response["answer"],
        tool_used="langchain_retriever"
    )

    db.add(conversation)
    db.commit()

    return response

@app.get("/conversations")
def get_conversations(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversations = db.query(Conversation).filter(
        Conversation.user_id == uuid.UUID(current_user["sub"])
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