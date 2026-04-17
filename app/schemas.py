from pydantic import BaseModel, EmailStr


class UserRegisterSchema(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str = "user"


class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

class TripPlanSchema(BaseModel):
    user_id: str
    source_location: str
    destination: str
    start_date: str
    end_date: str
    budget: int
    travelers_count: int

class UserPreferenceSchema(BaseModel):
    user_id: str
    budget_min: int | None = None
    budget_max: int | None = None
    preferred_transport: str | None = None
    preferred_hotel_type: str | None = None
    preferred_trip_type: str | None = None
    food_preference: str | None = None
    preferred_climate: str | None = None


class DestinationCompareSchema(BaseModel):
    destinations: list[str]


class BudgetOptimizeSchema(BaseModel):
    destination: str
    budget: int
    travelers: int = 1
    trip_days: int = 1
    preferred_transport: str = "flight"
    hotel_category: str = "3-star"
