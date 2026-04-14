import unittest
from unittest.mock import patch
import sys
import os

# add project root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.itinerary_service import (
    _parse_itinerary,
    _budget_breakdown,
    generate_itinerary
)

class TestItineraryService(unittest.TestCase):

    # =========================================================
    # TESTS FOR: _parse_itinerary (Testing the Regex Parsing Logic)
    # =========================================================
    
    def test_parse_itinerary_perfect_format(self):
        llm_response = """
        Day 1:
        Morning: Visit the Taj Mahal.
        Afternoon: Lunch at local cafe.
        Evening: Walk by the river.
        
        Day 2:
        Morning: Fort exploration.
        Afternoon: Shopping.
        Evening: Departure.
        """
        
        itinerary = _parse_itinerary(llm_response, total_days=2, destination="Agra")
        
        self.assertEqual(len(itinerary), 2)
        self.assertEqual(itinerary["day_1"]["morning"], "Visit the Taj Mahal.")
        self.assertEqual(itinerary["day_2"]["evening"], "Departure.")
        
    def test_parse_itinerary_missing_activities_fallback(self):
        # Scenario: The LLM output misses explicitly mentioning Afternoon or Evening.
        llm_response = """
        Day 1:
        Morning: Arrive and rest.
        """
        
        itinerary = _parse_itinerary(llm_response, total_days=1, destination="Paris")
        
        # It should parse the morning, and apply safe defaults for afternoon/evening
        self.assertEqual(itinerary["day_1"]["morning"], "Arrive and rest.")
        self.assertEqual(itinerary["day_1"]["afternoon"], "Enjoy local cuisine and sightseeing in Paris")
        self.assertEqual(itinerary["day_1"]["evening"], "Relax and explore local markets in Paris")

    def test_parse_itinerary_empty_response(self):
        # Scenario: The LLM completely fails to follow formatting, returning garbage text.
        llm_response = "I am sorry, I cannot generate this."
        
        itinerary = _parse_itinerary(llm_response, total_days=1, destination="Tokyo")
        
        # Should gracefully fall back to the generic default strings rather than crashing
        self.assertIn("day_1", itinerary)
        self.assertEqual(itinerary["day_1"]["morning"], "Explore top attractions in Tokyo")
        self.assertEqual(itinerary["day_1"]["afternoon"], "Enjoy local cuisine and sightseeing in Tokyo")
        self.assertEqual(itinerary["day_1"]["evening"], "Relax and explore local markets in Tokyo")


    # =========================================================
    # TESTS FOR: _budget_breakdown (Testing the Mathematical Logic)
    # =========================================================
    
    def test_budget_breakdown_luxury_flight(self):
        budget = 100000
        days = 5
        
        breakdown = _budget_breakdown(budget, days, transport="flight", hotel_type="5-star")
        
        # Logic check based on itinerary_service.py ratios:
        # Flight should be 30% -> 30,000
        # 5-star should be 40% -> 40,000
        # Food should be 20% -> 20,000
        # Misc should be 10% -> 10,000
        self.assertEqual(breakdown["transport"], 30000)
        self.assertEqual(breakdown["hotel_total"], 40000)
        self.assertEqual(breakdown["food"], 20000)
        self.assertEqual(breakdown["misc"], 10000)
        self.assertEqual(breakdown["hotel_per_night"], 8000) # 40000 / 5
        self.assertEqual(breakdown["grand_total"], 100000)

    def test_budget_breakdown_budget_bus(self):
        budget = 50000
        days = 2
        
        breakdown = _budget_breakdown(budget, days, transport="bus", hotel_type="budget")
        
        # Logic check based on itinerary_service.py ratios:
        # Bus/Other should be 15% -> 7,500
        # Budget/Other should be 20% -> 10,000
        # Food should be 20% -> 10,000
        # Misc should be 45% -> 22,500
        self.assertEqual(breakdown["transport"], 7500)
        self.assertEqual(breakdown["hotel_total"], 10000)
        self.assertEqual(breakdown["food"], 10000)
        self.assertEqual(breakdown["misc"], 22500)
        self.assertEqual(breakdown["grand_total"], 50000)

    def test_budget_breakdown_zero_days(self):
        # Scenario: What if start and end date are somehow messed up and days = 0?
        # The logic has `max(total_days, 1)` to prevent ZeroDivisionError, let's test it.
        breakdown = _budget_breakdown(budget=10000, total_days=0, transport="train", hotel_type="3-star")
        
        # 30% train + 30% 3-star + 20% food + 20% misc = 100%
        self.assertEqual(breakdown["hotel_per_night"], 3000) # 3000 / max(0, 1) = 3000

    # =========================================================
    # TESTS FOR: generate_itinerary (Testing the Public Function with API Mocking)
    # =========================================================
    
    # We patch "ask_groq_llm" so that we don't actually hit the LLM server during testing!
    # Instead, the mock_ask_groq_llm will simulate returning data instantly.
    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_full_flow(self, mock_ask_groq_llm):
        # 1. Setup Mock
        mock_ask_groq_llm.return_value = """
        Day 1:
        Morning: Start your day!
        Afternoon: Continue your day!
        Evening: End your day!
        """
        
        # 2. Define inputs
        preferences = {
            "trip_type": "adventure",
            "transport": "train",
            "hotel_type": "3-star",
            "food_preference": "vegan",
            "climate": "cold",
        }
        
        # 3. Execution
        itinerary, recommendations = generate_itinerary(
            source="Delhi",
            destination="Shimla",
            start_date="2026-05-01",
            end_date="2026-05-02",  # 2 days total
            budget=20000,
            travelers=2,
            destination_context="Hilly region, scenic.",
            preferences=preferences
        )
        
        # 4. Assertions
        # Ensure that our application actually attempted to ask the LLM once
        mock_ask_groq_llm.assert_called_once()
        
        # Check that the mocked string was properly parsed into days
        self.assertIn("day_1", itinerary)
        self.assertIn("day_2", itinerary)
        
        # Ensure preferences were integrated into recommendations successfully
        self.assertEqual(recommendations["total_days"], 2)
        self.assertEqual(recommendations["transport"], "train")
        self.assertEqual(recommendations["trip_type"], "adventure")
        self.assertIn("budget_breakdown", recommendations)
        
    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_defaults(self, mock_ask_groq_llm):
        mock_ask_groq_llm.return_value = "Day 1:\nMorning: Test"
        
        # Executing WITHOUT passing 'preferences'
        itinerary, recommendations = generate_itinerary(
            source="Mumbai",
            destination="Pune",
            start_date="2026-05-01",
            end_date="2026-05-01", 
            budget=5000,
            travelers=1
        )
        
        # Assert that the system falls back safely to default preferences
        self.assertEqual(recommendations["transport"], "flight")
        self.assertEqual(recommendations["hotel"], "3-star")
        self.assertEqual(recommendations["food_preference"], "vegetarian")

    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_api_failure(self, mock_ask_groq_llm):
        # Scenario: The external API is down or times out, raising an Exception
        mock_ask_groq_llm.side_effect = Exception("API Timeout")
        
        with self.assertRaises(Exception) as context:
            generate_itinerary(
                source="Delhi",
                destination="Jaipur",
                start_date="2026-06-01",
                end_date="2026-06-02", 
                budget=10000,
                travelers=2
            )
            
        self.assertIn("API Timeout", str(context.exception))

    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_inverted_dates(self, mock_ask_groq_llm):
        # Scenario: The start date is AFTER the end date
        mock_ask_groq_llm.return_value = ""
        
        # total_days should be negative, but code shouldn't crash
        itinerary, recommendations = generate_itinerary(
            source="Delhi",
            destination="Agra",
            start_date="2026-06-05",
            end_date="2026-06-01", # End is before start
            budget=10000,
            travelers=1
        )
        
        # Total days calculated would be -3, but max(total_days, 1) prevents zero division.
        # Check that it executed gracefully without crashing.
        self.assertEqual(recommendations["total_days"], -3)
        self.assertEqual(itinerary, {}) # Range loop in parser will be empty

    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_none_context(self, mock_ask_groq_llm):
        # Scenario: destination_context is passed as exactly None instead of empty string
        mock_ask_groq_llm.return_value = "Day 1:\nMorning: Test"
        
        # Because the code does `destination_context.strip() if destination_context`, 
        # testing if a NoneType causes an AttributeError
        try:
            generate_itinerary(
                source="Delhi",
                destination="Agra",
                start_date="2026-06-01",
                end_date="2026-06-02",
                budget=10000,
                travelers=1,
                destination_context=None # Hard None
            )
        except Exception as e:
            self.fail(f"generate_itinerary crashed on None context with error: {e}")

if __name__ == "__main__":
    unittest.main()
