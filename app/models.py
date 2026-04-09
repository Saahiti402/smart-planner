import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Integer,
    ForeignKey,
    Date
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    preferences = relationship("UserPreference", back_populates="user", uselist=False)
    trips = relationship("Trip", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    memories = relationship("MemoryStore", back_populates="user")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        unique=True
    )

    budget_min = Column(Integer, nullable=True)
    budget_max = Column(Integer, nullable=True)

    preferred_transport = Column(String(50), nullable=True)
    preferred_hotel_type = Column(String(50), nullable=True)
    preferred_trip_type = Column(String(50), nullable=True)
    food_preference = Column(String(50), nullable=True)
    preferred_climate = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship(
        "User",
        back_populates="preferences"
    )


class Trip(Base):
    __tablename__ = "trips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    source_location = Column(String(100))
    destination = Column(String(100))
    start_date = Column(Date)
    end_date = Column(Date)
    budget = Column(Integer)
    travelers_count = Column(Integer)
    status = Column(String(20), default="planned")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="trips")
    itineraries = relationship("Itinerary", back_populates="trip")


class Itinerary(Base):
    __tablename__ = "itineraries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id"))
    day_plan = Column(JSONB)
    estimated_cost = Column(Integer)
    recommendations = Column(JSONB)
    generated_by_agent = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    trip = relationship("Trip", back_populates="itineraries")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    session_id = Column(UUID(as_uuid=True), default=uuid.uuid4)
    user_message = Column(Text)
    assistant_response = Column(Text)
    tool_used = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="conversations")


class MemoryStore(Base):
    __tablename__ = "memory_store"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    memory_key = Column(String(100))
    memory_value = Column(Text)
    memory_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="memories")