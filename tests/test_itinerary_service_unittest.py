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

    # =========================================================
    # ADDITIONAL TEST CASES — Extended Coverage
    # =========================================================

    # ── 12. _parse_itinerary: 5-day trip, all days present ─────────────────
    def test_parse_itinerary_five_days_all_present(self):
        """All 5 days fully formatted — verifies multi-day loop is correct."""
        lines = []
        for d in range(1, 6):
            lines.append(f"Day {d}:\nMorning: Morning activity {d}.\nAfternoon: Afternoon activity {d}.\nEvening: Evening activity {d}.")
        llm_response = "\n".join(lines)

        itinerary = _parse_itinerary(llm_response, total_days=5, destination="Kerala")

        self.assertEqual(len(itinerary), 5)
        for d in range(1, 6):
            self.assertIn(f"day_{d}", itinerary)
            self.assertIn(f"Morning activity {d}.", itinerary[f"day_{d}"]["morning"])

    # ── 13. _parse_itinerary: keys always present even for unmatched days ──
    def test_parse_itinerary_all_keys_always_present(self):
        """Every day dict must always have morning, afternoon, evening keys."""
        itinerary = _parse_itinerary("", total_days=3, destination="Leh")

        for d in range(1, 4):
            day = itinerary[f"day_{d}"]
            self.assertIn("morning",   day)
            self.assertIn("afternoon", day)
            self.assertIn("evening",   day)

    # ── 14. _parse_itinerary: destination name appears in fallback text ─────
    def test_parse_itinerary_fallback_contains_destination(self):
        """Default fallback strings must include the destination name."""
        itinerary = _parse_itinerary("", total_days=1, destination="Mysore")

        self.assertIn("Mysore", itinerary["day_1"]["morning"])
        self.assertIn("Mysore", itinerary["day_1"]["afternoon"])
        self.assertIn("Mysore", itinerary["day_1"]["evening"])

    # ── 15. _budget_breakdown: train transport ratio (30%) ──────────────────
    def test_budget_breakdown_train_transport(self):
        """Train should use the 30% transport ratio (same as flight)."""
        breakdown = _budget_breakdown(budget=60000, total_days=3, transport="train", hotel_type="3-star")

        # Train = 30%, 3-star = 30%, food = 20%, misc = 20%
        self.assertEqual(breakdown["transport"], 18000)
        self.assertEqual(breakdown["hotel_total"], 18000)
        self.assertEqual(breakdown["food"], 12000)
        self.assertEqual(breakdown["grand_total"], 60000)

    # ── 16. _budget_breakdown: hotel_per_night calculation accuracy ─────────
    def test_budget_breakdown_hotel_per_night_accuracy(self):
        """hotel_per_night must equal hotel_total / total_days exactly."""
        breakdown = _budget_breakdown(budget=90000, total_days=9, transport="flight", hotel_type="3-star")

        expected_hotel_total    = round(90000 * 0.30)   # 3-star = 30%
        expected_hotel_per_night = round(expected_hotel_total / 9)
        self.assertEqual(breakdown["hotel_per_night"], expected_hotel_per_night)

    # ── 17. _budget_breakdown: all required keys present ────────────────────
    def test_budget_breakdown_all_keys_present(self):
        """Response dict must always have every expected key."""
        breakdown = _budget_breakdown(budget=20000, total_days=2, transport="bus", hotel_type="budget")

        required_keys = ["hotel_per_night", "hotel_total", "transport", "food", "misc", "grand_total"]
        for key in required_keys:
            self.assertIn(key, breakdown, msg=f"Missing key: {key}")

    # ── 18. generate_itinerary: large traveler count ────────────────────────
    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_large_traveler_count(self, mock_llm):
        """Should handle 15 travelers without any crash."""
        mock_llm.return_value = "Day 1:\nMorning: Group tour.\nAfternoon: Lunch.\nEvening: Rest."

        itinerary, recommendations = generate_itinerary(
            source="Delhi", destination="Agra",
            start_date="2026-07-01", end_date="2026-07-02",
            budget=300000, travelers=15
        )

        self.assertEqual(recommendations["travelers"], 15)
        self.assertIn("day_1", itinerary)

    # ── 19. generate_itinerary: single traveler solo trip ───────────────────
    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_single_traveler(self, mock_llm):
        """Single traveler solo budget — per_person_budget equals total budget."""
        mock_llm.return_value = "Day 1:\nMorning: Solo hike.\nAfternoon: Lunch.\nEvening: Hostel check-in."

        itinerary, recommendations = generate_itinerary(
            source="Bangalore", destination="Coorg",
            start_date="2026-08-01", end_date="2026-08-03",
            budget=15000, travelers=1
        )

        self.assertEqual(recommendations["travelers"], 1)
        self.assertEqual(recommendations["total_days"], 3)
        self.assertIn("day_1", itinerary)
        self.assertIn("day_3", itinerary)

    # ── 20. generate_itinerary: LLM prompt includes key fields ──────────────
    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_prompt_contains_key_info(self, mock_llm):
        """The prompt passed to LLM must contain source, destination, and budget."""
        mock_llm.return_value = "Day 1:\nMorning: Test.\nAfternoon: Test.\nEvening: Test."

        generate_itinerary(
            source="Chennai", destination="Ooty",
            start_date="2026-09-01", end_date="2026-09-02",
            budget=12000, travelers=2
        )

        # Capture the actual prompt that was sent to the LLM
        call_args = mock_llm.call_args[0][0]   # first positional argument
        self.assertIn("Chennai",     call_args)
        self.assertIn("Ooty",        call_args)
        self.assertIn("12,000",      call_args)   # budget formatted with comma
        self.assertIn("2026-09-01",  call_args)
        self.assertIn("2026-09-02",  call_args)

    # =========================================================
    # BATCH 3 — 30 MORE TEST CASES (21 – 50)
    # =========================================================

    # ────────────────────────────────────────────────────────
    # GROUP A: _parse_itinerary — deeper edge cases (21–30)
    # ────────────────────────────────────────────────────────

    def test_parse_itinerary_returns_dict(self):
        """21. Return type must always be a dictionary."""
        result = _parse_itinerary("Some random text", total_days=1, destination="Delhi")
        self.assertIsInstance(result, dict)

    def test_parse_itinerary_values_are_strings(self):
        """22. All time-block values (morning/afternoon/evening) must be strings."""
        itinerary = _parse_itinerary("", total_days=2, destination="Goa")
        for day_key, blocks in itinerary.items():
            self.assertIsInstance(blocks["morning"],   str)
            self.assertIsInstance(blocks["afternoon"], str)
            self.assertIsInstance(blocks["evening"],   str)

    def test_parse_itinerary_single_day_returns_one_entry(self):
        """23. A 1-day trip must produce exactly one entry in the dict."""
        itinerary = _parse_itinerary("Day 1:\nMorning: Arrive.\nAfternoon: Explore.\nEvening: Dinner.", 1, "Kochi")
        self.assertEqual(len(itinerary), 1)
        self.assertIn("day_1", itinerary)

    def test_parse_itinerary_ten_day_trip_count(self):
        """24. A 10-day trip must produce exactly 10 entries."""
        itinerary = _parse_itinerary("", total_days=10, destination="Europe")
        self.assertEqual(len(itinerary), 10)

    def test_parse_itinerary_evening_only_block(self):
        """25. When only Evening is present, morning & afternoon should be defaults."""
        llm_response = "Day 1:\nEvening: Attend cultural show."
        itinerary = _parse_itinerary(llm_response, total_days=1, destination="Jaipur")
        self.assertEqual(itinerary["day_1"]["morning"],  "Explore top attractions in Jaipur")
        self.assertEqual(itinerary["day_1"]["afternoon"],"Enjoy local cuisine and sightseeing in Jaipur")
        self.assertIn("Attend cultural show", itinerary["day_1"]["evening"])

    def test_parse_itinerary_afternoon_only_block(self):
        """26. When only Afternoon is present, morning & evening should be defaults."""
        llm_response = "Day 1:\nAfternoon: Boat ride on the lake."
        itinerary = _parse_itinerary(llm_response, total_days=1, destination="Kashmir")
        self.assertEqual(itinerary["day_1"]["morning"],  "Explore top attractions in Kashmir")
        self.assertIn("Boat ride", itinerary["day_1"]["afternoon"])
        self.assertEqual(itinerary["day_1"]["evening"],  "Relax and explore local markets in Kashmir")

    def test_parse_itinerary_no_duplicate_day_keys(self):
        """27. There should be no duplicate keys in the returned itinerary."""
        itinerary = _parse_itinerary("", total_days=5, destination="Rajasthan")
        keys = list(itinerary.keys())
        self.assertEqual(len(keys), len(set(keys)))

    def test_parse_itinerary_destination_with_spaces(self):
        """28. Destination with spaces (e.g., 'New Delhi') must appear in fallback text."""
        itinerary = _parse_itinerary("", total_days=1, destination="New Delhi")
        self.assertIn("New Delhi", itinerary["day_1"]["morning"])

    def test_parse_itinerary_day_keys_are_sequential(self):
        """29. Day keys must be day_1, day_2, ... in exact sequence."""
        itinerary = _parse_itinerary("", total_days=4, destination="Manali")
        expected_keys = {"day_1", "day_2", "day_3", "day_4"}
        self.assertEqual(set(itinerary.keys()), expected_keys)

    def test_parse_itinerary_non_empty_fallback_strings(self):
        """30. Fallback strings must never be empty — always meaningful text."""
        itinerary = _parse_itinerary("", total_days=1, destination="Rishikesh")
        self.assertTrue(len(itinerary["day_1"]["morning"]) > 0)
        self.assertTrue(len(itinerary["day_1"]["afternoon"]) > 0)
        self.assertTrue(len(itinerary["day_1"]["evening"]) > 0)

    # ────────────────────────────────────────────────────────
    # GROUP B: _budget_breakdown — parametric math tests (31–40)
    # ────────────────────────────────────────────────────────

    def test_budget_breakdown_car_transport_ratio(self):
        """31. Car transport must use the 15% ratio (non-flight/train)."""
        breakdown = _budget_breakdown(budget=40000, total_days=4, transport="car", hotel_type="3-star")
        self.assertEqual(breakdown["transport"], 6000)   # 15% of 40000

    def test_budget_breakdown_luxury_hotel_ratio(self):
        """32. 'luxury' hotel string must trigger the 40% hotel ratio."""
        breakdown = _budget_breakdown(budget=100000, total_days=5, transport="bus", hotel_type="luxury")
        self.assertEqual(breakdown["hotel_total"], 40000)  # 40% of 100000

    def test_budget_breakdown_4star_hotel_falls_to_20_percent(self):
        """33. '4-star' does not match '5-star' or '3-star' → should use 20% ratio."""
        breakdown = _budget_breakdown(budget=50000, total_days=5, transport="bus", hotel_type="4-star")
        self.assertEqual(breakdown["hotel_total"], 10000)  # 20% of 50000

    def test_budget_breakdown_food_always_20_percent(self):
        """34. Food allocation must always be exactly 20% regardless of other params."""
        for transport, hotel in [("flight", "5-star"), ("bus", "budget"), ("train", "3-star")]:
            breakdown = _budget_breakdown(budget=80000, total_days=4, transport=transport, hotel_type=hotel)
            self.assertEqual(breakdown["food"], 16000,  # 20% of 80000
                msg=f"Food not 20% for transport={transport}, hotel={hotel}")

    def test_budget_breakdown_misc_never_negative(self):
        """35. Misc budget must never go negative, even in extreme ratio combinations."""
        breakdown = _budget_breakdown(budget=10000, total_days=1, transport="flight", hotel_type="5-star")
        self.assertGreaterEqual(breakdown["misc"], 0)

    def test_budget_breakdown_grand_total_equals_parts_sum(self):
        """36. grand_total must equal hotel_total + transport + food + misc."""
        breakdown = _budget_breakdown(budget=75000, total_days=5, transport="train", hotel_type="4-star")
        calculated = breakdown["hotel_total"] + breakdown["transport"] + breakdown["food"] + breakdown["misc"]
        self.assertEqual(breakdown["grand_total"], calculated)

    def test_budget_breakdown_one_night_trip_hotel_per_night(self):
        """37. For 1-day trip, hotel_per_night must equal hotel_total."""
        breakdown = _budget_breakdown(budget=30000, total_days=1, transport="flight", hotel_type="3-star")
        self.assertEqual(breakdown["hotel_per_night"], breakdown["hotel_total"])

    def test_budget_breakdown_large_budget(self):
        """38. Should handle very large budgets (₹10,00,000) without overflow."""
        breakdown = _budget_breakdown(budget=1000000, total_days=10, transport="flight", hotel_type="5-star")
        self.assertEqual(breakdown["transport"],  300000)  # 30%
        self.assertEqual(breakdown["hotel_total"], 400000)  # 40%
        self.assertEqual(breakdown["food"],        200000)  # 20%

    def test_budget_breakdown_minimal_budget(self):
        """39. Should handle minimal budget (₹1000) without crashing."""
        breakdown = _budget_breakdown(budget=1000, total_days=1, transport="bus", hotel_type="budget")
        self.assertIn("grand_total", breakdown)
        self.assertGreater(breakdown["grand_total"], 0)

    def test_budget_breakdown_hotel_per_night_is_integer(self):
        """40. hotel_per_night must always be an integer (round() applied)."""
        breakdown = _budget_breakdown(budget=55555, total_days=7, transport="train", hotel_type="3-star")
        self.assertIsInstance(breakdown["hotel_per_night"], int)

    # ────────────────────────────────────────────────────────
    # GROUP C: generate_itinerary — integration & output shape (41–50)
    # ────────────────────────────────────────────────────────

    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_returns_tuple(self, mock_llm):
        """41. generate_itinerary must return a 2-tuple (itinerary, recommendations)."""
        mock_llm.return_value = "Day 1:\nMorning: Test.\nAfternoon: Test.\nEvening: Test."
        result = generate_itinerary("Delhi","Agra","2026-10-01","2026-10-02", 10000, 2)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_recommendations_has_hotel_key(self, mock_llm):
        """42. Recommendations dict must contain 'hotel' key."""
        mock_llm.return_value = "Day 1:\nMorning: T.\nAfternoon: T.\nEvening: T."
        _, recommendations = generate_itinerary("A","B","2026-10-01","2026-10-02", 10000, 1)
        self.assertIn("hotel", recommendations)

    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_recommendations_has_food_preference(self, mock_llm):
        """43. Recommendations dict must contain 'food_preference' key."""
        mock_llm.return_value = "Day 1:\nMorning: T.\nAfternoon: T.\nEvening: T."
        _, recommendations = generate_itinerary("A","B","2026-10-01","2026-10-02", 10000, 1)
        self.assertIn("food_preference", recommendations)

    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_recommendations_has_climate(self, mock_llm):
        """44. Recommendations dict must contain 'climate' key."""
        mock_llm.return_value = "Day 1:\nMorning: T.\nAfternoon: T.\nEvening: T."
        _, recommendations = generate_itinerary("A","B","2026-10-01","2026-10-02", 10000, 1)
        self.assertIn("climate", recommendations)

    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_recommendations_has_trip_type(self, mock_llm):
        """45. Recommendations dict must contain 'trip_type' key."""
        mock_llm.return_value = "Day 1:\nMorning: T.\nAfternoon: T.\nEvening: T."
        _, recommendations = generate_itinerary("A","B","2026-10-01","2026-10-02", 10000, 1)
        self.assertIn("trip_type", recommendations)

    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_recommendations_has_total_days(self, mock_llm):
        """46. Recommendations must contain 'total_days' matching date math."""
        mock_llm.return_value = "Day 1:\nMorning: T.\nAfternoon: T.\nEvening: T."
        _, recommendations = generate_itinerary("A","B","2026-10-01","2026-10-05", 20000, 2)
        self.assertEqual(recommendations["total_days"], 5)

    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_day_keys_match_total_days(self, mock_llm):
        """47. Number of day_N keys in itinerary must equal total_days."""
        mock_llm.return_value = "\n".join(
            [f"Day {d}:\nMorning: T.\nAfternoon: T.\nEvening: T." for d in range(1,8)]
        )
        itinerary, recommendations = generate_itinerary(
            "Mumbai","Goa","2026-11-01","2026-11-07", 40000, 3
        )
        self.assertEqual(len(itinerary), recommendations["total_days"])

    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_honeymoon_trip_type(self, mock_llm):
        """48. Honeymoon trip_type preference must be stored correctly."""
        mock_llm.return_value = "Day 1:\nMorning: T.\nAfternoon: T.\nEvening: T."
        _, recommendations = generate_itinerary(
            "Chennai","Maldives","2026-12-01","2026-12-05", 200000, 2,
            preferences={"trip_type": "honeymoon", "transport": "flight",
                         "hotel_type": "5-star", "food_preference": "any", "climate": "tropical"}
        )
        self.assertEqual(recommendations["trip_type"], "honeymoon")

    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_business_trip_type(self, mock_llm):
        """49. Business trip_type preference must be stored correctly."""
        mock_llm.return_value = "Day 1:\nMorning: T.\nAfternoon: T.\nEvening: T."
        _, recommendations = generate_itinerary(
            "Hyderabad","Pune","2026-11-10","2026-11-12", 30000, 1,
            preferences={"trip_type": "business", "transport": "flight",
                         "hotel_type": "4-star", "food_preference": "any", "climate": "moderate"}
        )
        self.assertEqual(recommendations["trip_type"], "business")

    @patch('app.services.itinerary_service.ask_groq_llm')
    def test_generate_itinerary_30_day_long_trip(self, mock_llm):
        """50. A 30-day long trip must produce 30 day entries without crash."""
        days_text = "\n".join(
            [f"Day {d}:\nMorning: T.\nAfternoon: T.\nEvening: T." for d in range(1, 31)]
        )
        mock_llm.return_value = days_text
        itinerary, recommendations = generate_itinerary(
            "India","Europe","2026-06-01","2026-06-30", 500000, 4
        )
        self.assertEqual(recommendations["total_days"], 30)
        self.assertEqual(len(itinerary), 30)
        self.assertIn("day_30", itinerary)

if __name__ == "__main__":
    unittest.main()
