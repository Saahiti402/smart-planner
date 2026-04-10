from __future__ import annotations

import math
import os
from typing import Literal, Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator


router = APIRouter(prefix="/tools", tags=["External Travel Tool"])

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")


def _require_api_key(value: Optional[str], env_name: str, source_name: str) -> str:
    if not value:
        raise HTTPException(
            status_code=500,
            detail=f"{source_name} API key is missing. Set {env_name} in your environment.",
        )
    return value


class ExternalTravelToolRequest(BaseModel):
    type: Literal["weather", "places", "transport", "flights"]
    city: Optional[str] = None
    start: Optional[str] = Field(
        default=None,
        description="Latitude and longitude in the format 'lat,lon'",
    )
    end: Optional[str] = Field(
        default=None,
        description="Latitude and longitude in the format 'lat,lon'",
    )

    @field_validator("city")
    @classmethod
    def normalize_city(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @field_validator("start", "end")
    @classmethod
    def normalize_coordinates(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


def _safe_get_json(url: str, params: dict, source: str) -> dict:
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"{source} request failed: {exc}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"{source} returned invalid JSON response",
        ) from exc


def _parse_lat_lon(value: str, field_name: str) -> tuple[float, float]:
    try:
        lat_text, lon_text = value.split(",", 1)
        lat = float(lat_text.strip())
        lon = float(lon_text.strip())
    except (ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}. Use 'lat,lon' format.",
        ) from exc

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name} coordinates. Latitude must be between -90 and 90 and longitude between -180 and 180.",
        )

    return lat, lon


def _haversine_distance_km(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> float:
    radius_km = 6371.0
    d_lat = math.radians(end_lat - start_lat)
    d_lon = math.radians(end_lon - start_lon)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(start_lat))
        * math.cos(math.radians(end_lat))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def _estimate_travel_time(distance_km: float) -> dict:
    average_speed_kmh = 45.0
    hours = distance_km / average_speed_kmh if distance_km > 0 else 0.0
    total_minutes = max(1, int(round(hours * 60))) if distance_km > 0 else 0
    return {
        "hours": round(hours, 2),
        "minutes": total_minutes,
        "estimated_speed_kmh": average_speed_kmh,
    }


def _get_weather(city: str) -> dict:
    api_key = _require_api_key(
        OPENWEATHER_API_KEY,
        "OPENWEATHER_API_KEY",
        "OpenWeather",
    )
    url = "http://api.openweathermap.org/data/2.5/weather"
    payload = _safe_get_json(
        url,
        {
            "q": city,
            "appid": api_key,
            "units": "metric",
        },
        "OpenWeather",
    )

    weather_list = payload.get("weather") or []
    weather_description = ""
    if weather_list and isinstance(weather_list, list):
        weather_description = weather_list[0].get("description", "")

    return {
        "type": "weather",
        "data": {
            "city": payload.get("name", city),
            "temperature": payload.get("main", {}).get("temp"),
            "weather_description": weather_description,
        },
        "source": "OpenWeather",
    }


def _geocode_city(city: str) -> tuple[float, float]:
    api_key = _require_api_key(
        GEOAPIFY_API_KEY,
        "GEOAPIFY_API_KEY",
        "Geoapify",
    )
    payload = _safe_get_json(
        "https://api.geoapify.com/v1/geocode/search",
        {
            "text": city,
            "limit": 1,
            "apiKey": api_key,
        },
        "Geoapify Geocoding",
    )

    features = payload.get("features", [])
    if not features:
        raise HTTPException(
            status_code=404,
            detail=f"Could not geocode city '{city}' for place lookup.",
        )

    geometry = features[0].get("geometry", {})
    coordinates = geometry.get("coordinates", [])
    if len(coordinates) < 2:
        raise HTTPException(
            status_code=502,
            detail=f"Geoapify geocoding did not return coordinates for '{city}'.",
        )

    lon, lat = coordinates[0], coordinates[1]
    return float(lat), float(lon)


def _get_places(city: str) -> dict:
    api_key = _require_api_key(
        GEOAPIFY_API_KEY,
        "GEOAPIFY_API_KEY",
        "Geoapify",
    )
    url = "https://api.geoapify.com/v2/places"

    try:
        payload = _safe_get_json(
            url,
            {
                "categories": "tourism",
                "filter": f"city:{city}",
                "limit": 5,
                "apiKey": api_key,
            },
            "Geoapify",
        )
    except HTTPException:
        lat, lon = _geocode_city(city)
        payload = _safe_get_json(
            url,
            {
                "categories": "tourism",
                "filter": f"circle:{lon},{lat},10000",
                "limit": 5,
                "apiKey": api_key,
            },
            "Geoapify",
        )

    features = payload.get("features", [])
    top_places = []
    for feature in features[:5]:
        properties = feature.get("properties", {})
        name = properties.get("name") or properties.get("formatted")
        if name:
            top_places.append(name)

    return {
        "type": "places",
        "data": {
            "city": city,
            "top_places": top_places,
        },
        "source": "Geoapify",
    }


def _get_transport(start: str, end: str) -> dict:
    start_lat, start_lon = _parse_lat_lon(start, "start")
    end_lat, end_lon = _parse_lat_lon(end, "end")

    distance_km = _haversine_distance_km(start_lat, start_lon, end_lat, end_lon)
    travel_time = _estimate_travel_time(distance_km)

    return {
        "type": "transport",
        "data": {
            "start": {"lat": start_lat, "lon": start_lon},
            "end": {"lat": end_lat, "lon": end_lon},
            "distance_km": round(distance_km, 2),
            "estimated_travel_time": travel_time,
            "note": "Estimated using haversine distance and average road speed fallback.",
        },
        "source": "Geoapify Route Estimate / Haversine Fallback",
    }


def _get_flights() -> dict:
    api_key = _require_api_key(
        AVIATIONSTACK_API_KEY,
        "AVIATIONSTACK_API_KEY",
        "Aviationstack",
    )
    url = "http://api.aviationstack.com/v1/flights"
    payload = _safe_get_json(
        url,
        {
            "access_key": api_key,
            "limit": 3,
        },
        "Aviationstack",
    )

    flight_data = payload.get("data", [])
    top_flights = []

    for flight in flight_data[:3]:
        airline = flight.get("airline", {})
        departure = flight.get("departure", {})
        arrival = flight.get("arrival", {})
        top_flights.append(
            {
                "flight_date": flight.get("flight_date"),
                "flight_status": flight.get("flight_status"),
                "airline": airline.get("name"),
                "departure_airport": departure.get("airport"),
                "departure_city": departure.get("city"),
                "arrival_airport": arrival.get("airport"),
                "arrival_city": arrival.get("city"),
                "flight_number": flight.get("flight", {}).get("number"),
            }
        )

    return {
        "type": "flights",
        "data": {
            "flights": top_flights,
        },
        "source": "Aviationstack",
    }


@router.post("/external-travel")
def external_travel_tool(request: ExternalTravelToolRequest):
    try:
        if request.type == "weather":
            if not request.city:
                raise HTTPException(
                    status_code=400,
                    detail="'city' is required for weather requests.",
                )
            return _get_weather(request.city)

        if request.type == "places":
            if not request.city:
                raise HTTPException(
                    status_code=400,
                    detail="'city' is required for places requests.",
                )
            return _get_places(request.city)

        if request.type == "transport":
            if not request.start or not request.end:
                raise HTTPException(
                    status_code=400,
                    detail="'start' and 'end' are required for transport requests.",
                )
            return _get_transport(request.start, request.end)

        if request.type == "flights":
            return _get_flights()

        raise HTTPException(
            status_code=400,
            detail="Invalid type. Use weather, places, transport, or flights.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error in external travel tool: {exc}",
        ) from exc