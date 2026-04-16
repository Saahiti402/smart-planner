import os
import requests
import functools
import re
from langchain_core.tools import tool
from datetime import datetime, timedelta

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# IATA code mapper
CITY_TO_IATA = {
    "bangalore": "BLR",
    "bengaluru": "BLR", 
    "mumbai": "BOM",
    "delhi": "DEL",
    "new delhi": "DEL",
    "chennai": "MAA",
    "hyderabad": "HYD",
    "kolkata": "CCU",
    "goa": "GOI",
    "pune": "PNQ",
    "london": "LHR",
    "paris": "CDG",
    "dubai": "DXB",
    "singapore": "SIN",
    "tokyo": "NRT",
    "new york": "JFK"
}

from app.services.groq_llm_service import ask_groq_llm

@functools.lru_cache(maxsize=128)
def _get_iata(city: str) -> str:
    # 1. Check local generic dictionary natively
    code = CITY_TO_IATA.get(city.lower().strip())
    if code:
        return code
        
    # 2. Fallback to AI Dynamic Translation (Anywhere to Anywhere)
    try:
        prompt = f"Return ONLY the 3-letter IATA airport code for the city: '{city}'. Do not add any other text or punctuation."
        response = ask_groq_llm(prompt).strip().upper()
        
        match = re.search(r'[A-Z]{3}', response)
        if match:
            return match.group()
    except Exception:
        pass
        
    # 3. Ultimate Fallback
    return city.upper()

@functools.lru_cache(maxsize=128)
def _format_date(date_str: str) -> str:
    """Uses AI to parse any date string ('next Sunday', '15/06/2026') into YYYY-MM-DD format."""
    if not date_str:
        return ""
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str.strip()):
        return date_str.strip()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = (f"The user provided a travel date: '{date_str}'. Today's date is {today}. "
                  f"Convert the travel date into strict 'YYYY-MM-DD' format. "
                  f"Return ONLY the 10-character YYYY-MM-DD string, no extra text.")
        response = ask_groq_llm(prompt).strip()
        match = re.search(r'\d{4}-\d{2}-\d{2}', response)
        if match:
            return match.group()
    except Exception:
        pass
    return date_str.strip()

@functools.lru_cache(maxsize=128)
def _fetch_flights_data(origin: str, destination: str, date: str, return_date: str = None) -> str:
    try:
        origin_code = _get_iata(origin)
        dest_code = _get_iata(destination)
        safe_date = _format_date(date)
        safe_return_date = _format_date(return_date) if return_date else None
        
        params = {
            "engine": "google_flights",
            "departure_id": origin_code,
            "arrival_id": dest_code,
            "outbound_date": safe_date,  # format: YYYY-MM-DD
            "currency": "INR",
            "hl": "en",
            "api_key": SERPAPI_KEY
        }
        
        if safe_return_date:
            params["type"] = "1"  # Round trip
            params["return_date"] = safe_return_date
        else:
            params["type"] = "2"  # One way
            
        print(f"Fetching flights: {origin_code} → {dest_code} on {safe_date}" + (f" returning {safe_return_date}" if safe_return_date else " (One way)"))
        res = requests.get(
            "https://serpapi.com/search",
            params=params,
            timeout=15
        )
        print("Flights API status:", res.status_code)
        
        data = res.json()
        
        # SerpApi returns error in this field
        if "error" in data:
            return f"Flights API error: {data['error']}"
        
        flights = data.get("best_flights", []) or data.get("other_flights", [])
        
        if not flights:
            return f"No flights found from {origin_code} to {dest_code} on {date}."
        
        results = []
        for f in flights[:3]:
            first_leg = f["flights"][0]
            last_leg = f["flights"][-1]
            stops = len(f["flights"]) - 1
            stop_info = f" ({stops} stop)" if stops == 1 else (f" ({stops} stops)" if stops > 1 else " (Direct)")
            
            results.append(
                f"Airline: {first_leg.get('airline', 'N/A')}{stop_info}, "
                f"From: {first_leg.get('departure_airport', {}).get('name', origin_code)}, "
                f"To: {last_leg.get('arrival_airport', {}).get('name', dest_code)}, "
                f"Duration: {f.get('total_duration', 'N/A')} mins, "
                f"Price: ₹{f.get('price', 'N/A')}"
            )
        return "\n".join(results)
        
    except Exception as e:
        return f"Flights fetch failed: {str(e)}"


@functools.lru_cache(maxsize=128)
def _fetch_hotels_data(city: str, check_in: str, check_out: str) -> str:
    if not SERPAPI_KEY:
        return "Error: SERPAPI_KEY missing."
        
    safe_check_in = _format_date(check_in)
    safe_check_out = _format_date(check_out)
    
    params = {
        "engine": "google_hotels",
        "q": city,
        "check_in_date": safe_check_in,
        "check_out_date": safe_check_out,
        "hl": "en",
        "currency": "INR",
        "api_key": SERPAPI_KEY
    }
    try:
        resp = requests.get("https://serpapi.com/search", params=params)
        data = resp.json()
        properties = data.get("properties", [])
        if not properties:
            return "No hotels found."
        
        result = []
        for index, p in enumerate(properties[:3]):
            name = p.get("name", "Unknown")
            price = p.get("rate_per_night", {}).get("lowest", "Unknown price")
            rating = p.get("overall_rating", "No rating")
            result.append(f"{index+1}. Hotel: {name}, Price/Night: INR {price}, Rating: {rating}")
        return "\n".join(result)
    except Exception as e:
        return f"Error fetching hotels: {str(e)}"


@functools.lru_cache(maxsize=128)
def _fetch_weather_data(city: str) -> str:
    try:
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "cnt": 5
        }
        res = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params=params,
            timeout=10
        )
        print("Weather API status:", res.status_code)
        print("Weather API response:", res.text)  # debug line
        
        if res.status_code == 401:
            return "Weather API key is invalid or not activated yet. Wait 15 minutes after creating the key."
        
        if res.status_code != 200:
            return f"Weather API error: {res.status_code} - {res.text}"
        
        data = res.json()
        forecasts = data.get("list", [])
        
        if not forecasts:
            return "No weather data found for this city."
        
        results = []
        for f in forecasts[:5]:
            results.append(
                f"Time: {f['dt_txt']}, "
                f"Temp: {f['main']['temp']}°C, "
                f"Feels like: {f['main']['feels_like']}°C, "
                f"Weather: {f['weather'][0]['description']}"
            )
        return "\n".join(results)
        
    except Exception as e:
        return f"Weather fetch failed: {str(e)}"


@functools.lru_cache(maxsize=128)
def _fetch_activities_data(city: str) -> str:
    if not SERPAPI_KEY:
        return "Error: SERPAPI_KEY missing."
    params = {
        "engine": "google_maps",
        "q": f"top tourist attractions in {city}",
        "type": "search",
        "api_key": SERPAPI_KEY
    }
    try:
        resp = requests.get("https://serpapi.com/search", params=params)
        data = resp.json()
        local_results = data.get("local_results", [])
        if not local_results:
            return "No activities found."
        
        result = []
        for index, l in enumerate(local_results[:5]):
            name = l.get("title", "")
            rating = l.get("rating", "")
            addr = l.get("address", "")
            result.append(f"{index+1}. Place: {name}, Rating: {rating}, Address: {addr}")
        return "\n".join(result)
    except Exception as e:
        return f"Error fetching activities: {str(e)}"


# --- LangChain Tools ---

@tool
def fetch_flights(origin: str, destination: str, date: str, return_date: str = None) -> str:
    """Fetch flight info from SerpApi. If round trip, pass return_date (YYYY-MM-DD)."""
    return _fetch_flights_data(origin, destination, date, return_date)


@tool
def fetch_hotels(city: str, check_in: str, check_out: str) -> str:
    """Fetch hotel info from SerpApi."""
    return _fetch_hotels_data(city, check_in, check_out)


@tool
def fetch_weather(city: str) -> str:
    """Fetch weather forecast from OpenWeatherMap."""
    return _fetch_weather_data(city)


@tool
def fetch_activities(city: str) -> str:
    """Fetch tourist attractions from SerpApi."""
    return _fetch_activities_data(city)


@tool
def external_travel_tool(query: str) -> str:
    """
    Master LangChain tool acting as a router.
    Accepts a single string query and routes to the appropriate tool based on keywords.
    """
    q = query.lower()
    
    # Defaults and extracts for router purposes to satisfy the function requirements
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    if any(kw in q for kw in ["flight", "fly", "airline"]):
        # rudimentary fallback parsing for testing the router directly via a string query
        words = q.replace(",", " ").split()
        origin = words[words.index("from") + 1] if "from" in words and words.index("from") + 1 < len(words) else "DEL"
        dest = words[words.index("to") + 1] if "to" in words and words.index("to") + 1 < len(words) else "BOM"
        return _fetch_flights_data(origin.upper(), dest.upper(), today)
        
    elif any(kw in q for kw in ["hotel", "stay", "accommodation"]):
        # extracting city (fallback to a default, but assuming the city name is somewhere)
        city_match = re.search(r"in\s+(\w+)", q)
        city = city_match.group(1) if city_match else "Goa"
        return _fetch_hotels_data(city, today, tomorrow)
        
    elif any(kw in q for kw in ["weather", "temperature", "forecast"]):
        city_match = re.search(r"(?:in|for)\s+(\w+)", q)
        city = city_match.group(1) if city_match else "Goa"
        return _fetch_weather_data(city)
        
    elif any(kw in q for kw in ["activity", "attraction", "things to do", "places"]):
        city_match = re.search(r"in\s+(\w+)", q)
        city = city_match.group(1) if city_match else "Goa"
        return _fetch_activities_data(city)
        
    else:
        return "Please specify if you need flights, hotels, weather, or activities."
