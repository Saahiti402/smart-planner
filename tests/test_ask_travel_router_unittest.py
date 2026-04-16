import os
import sys
import types
import unittest
from datetime import datetime
from unittest.mock import patch

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)


langchain_service = types.ModuleType("app.services.langchain_service")
langchain_service.query_travel_assistant = lambda query, role="user": {
    "query": query,
    "answer": "stubbed rag answer",
    "source": "rag_llm",
}
sys.modules["app.services.langchain_service"] = langchain_service

destination_compare_service = types.ModuleType(
    "app.services.destination_compare_service"
)
destination_compare_service.compare_destinations = lambda cities: {
    "cities": cities
}
sys.modules[
    "app.services.destination_compare_service"
] = destination_compare_service

budget_service = types.ModuleType("app.services.budget_service")
budget_service.optimize_budget = lambda **kwargs: kwargs
sys.modules["app.services.budget_service"] = budget_service

external_travel_service = types.ModuleType(
    "app.services.external_travel_service"
)


class DummyTool:
    def invoke(self, query):
        return {"query": query}


external_travel_service.external_travel_tool = DummyTool()
sys.modules["app.services.external_travel_service"] = external_travel_service

itinerary_service = types.ModuleType("app.services.itinerary_service")
itinerary_service.generate_itinerary = lambda **kwargs: (
    {
        "day_1": {
            "morning": "Beach",
            "afternoon": "Lunch",
            "evening": "Market",
        },
        "day_2": {
            "morning": "Fort",
            "afternoon": "Cafe",
            "evening": "Return",
        },
    },
    {"total_days": 2},
)
sys.modules["app.services.itinerary_service"] = itinerary_service

trip_service = types.ModuleType("app.services.trip_service")
trip_service.query_user_trips = lambda db, user_id, query: {}
trip_service.get_latest_trip = lambda db, user_id: {}
trip_service.mark_latest_trip_completed = lambda db, user_id: {}
sys.modules["app.services.trip_service"] = trip_service

from app.services.ask_travel_router import (
    extract_budget_amount,
    extract_destination_from_query,
    extract_hotel_category,
    extract_transport,
    extract_travelers,
    extract_trip_days,
    is_budget_query,
    is_itinerary_query,
    is_trip_management_query,
    route_travel_query,
)


class TestAskTravelRouter(unittest.TestCase):

    def test_is_itinerary_query_matches_natural_language_plan(self):
        self.assertTrue(
            is_itinerary_query("plan a 2 day trip to goa")
        )

    def test_is_budget_query_matches_budget_optimizer_phrase(self):
        self.assertTrue(
            is_budget_query(
                "optimize budget for Goa for 2 people for 3 days under 30000"
            )
        )

    def test_is_trip_management_query_ignores_trip_days_phrase(self):
        self.assertFalse(
            is_trip_management_query(
                "destination is goa, 2 traveller, trip days 5, budget is 50000"
            )
        )

    def test_is_trip_management_query_matches_history_request(self):
        self.assertTrue(
            is_trip_management_query("show my trips")
        )

    def test_extract_trip_days_reads_numeric_duration(self):
        self.assertEqual(
            extract_trip_days("plan a 2 day trip to goa"),
            2
        )

    def test_extract_destination_from_query_reads_city(self):
        self.assertEqual(
            extract_destination_from_query(
                "plan a 2 day trip to goa"
            ),
            "goa"
        )

    def test_extract_budget_amount_prefers_larger_budget_number(self):
        self.assertEqual(
            extract_budget_amount(
                "optimize budget for Goa for 2 people for 3 days under 30000"
            ),
            30000
        )

    def test_extract_budget_amount_supports_k_suffix(self):
        self.assertEqual(
            extract_budget_amount(
                "goa trip under 45k for 2 people"
            ),
            45000
        )

    def test_extract_budget_amount_ignores_separator_commas(self):
        self.assertEqual(
            extract_budget_amount(
                "destination is goa,2 traveller, trip days.5,budget is 50,000"
            ),
            50000
        )

    def test_extract_travelers_reads_people_count(self):
        self.assertEqual(
            extract_travelers(
                "budget for Goa for 4 people under 50000"
            ),
            4
        )

    def test_extract_travelers_reads_singular_traveller(self):
        self.assertEqual(
            extract_travelers("destination is goa,2 traveller"),
            2
        )

    def test_extract_trip_days_reads_days_after_label(self):
        self.assertEqual(
            extract_trip_days("trip days.5", default=3),
            5
        )

    def test_extract_transport_reads_mode(self):
        self.assertEqual(
            extract_transport("goa budget under 40000 by train"),
            "train"
        )

    def test_extract_hotel_category_reads_hotel_tier(self):
        self.assertEqual(
            extract_hotel_category("goa budget under 40000 with 5 star stay"),
            "5-star"
        )

    @patch("app.services.ask_travel_router.generate_itinerary")
    def test_route_travel_query_generates_itinerary_for_two_day_trip(
        self,
        mock_generate_itinerary
    ):
        mock_generate_itinerary.return_value = (
            {
                "day_1": {"morning": "Beach", "afternoon": "Lunch", "evening": "Market"},
                "day_2": {"morning": "Fort", "afternoon": "Cafe", "evening": "Return"},
            },
            {"total_days": 2}
        )

        result = route_travel_query(
            query="plan a 2 day trip to goa",
            role="user"
        )

        self.assertEqual(result["tool_used"], "itinerary_tool")
        kwargs = mock_generate_itinerary.call_args.kwargs
        self.assertEqual(kwargs["destination"], "Goa")

        start = datetime.strptime(
            kwargs["start_date"],
            "%Y-%m-%d"
        )
        end = datetime.strptime(
            kwargs["end_date"],
            "%Y-%m-%d"
        )
        self.assertEqual((end - start).days, 1)

    @patch("app.services.ask_travel_router.optimize_budget")
    def test_route_travel_query_builds_budget_request_from_chat(
        self,
        mock_optimize_budget
    ):
        mock_optimize_budget.return_value = {
            "budget_allocation": {"hotel": 10000, "transport": 8000}
        }

        result = route_travel_query(
            query=(
                "optimize budget for Goa for 2 people "
                "for 3 days under 30000 by train"
            ),
            role="user"
        )

        self.assertEqual(result["tool_used"], "budget_tool")
        kwargs = mock_optimize_budget.call_args.kwargs
        self.assertEqual(kwargs["destination"], "Goa")
        self.assertEqual(kwargs["total_budget"], 30000)
        self.assertEqual(kwargs["travelers"], 2)
        self.assertEqual(kwargs["trip_days"], 3)
        self.assertEqual(kwargs["preferred_transport"], "train")

    @patch("app.services.ask_travel_router.optimize_budget")
    def test_route_travel_query_uses_saved_preferences_for_budget_defaults(
        self,
        mock_optimize_budget
    ):
        mock_optimize_budget.return_value = {
            "budget_allocation": {"hotel": 10000, "transport": 8000}
        }

        result = route_travel_query(
            query="optimize budget for goa",
            role="user",
            preferences={
                "budget_max": 80000,
                "preferred_transport": "bus",
                "preferred_hotel_type": "budget",
            }
        )

        self.assertEqual(result["tool_used"], "budget_tool")
        kwargs = mock_optimize_budget.call_args.kwargs
        self.assertEqual(kwargs["total_budget"], 80000)
        self.assertEqual(kwargs["preferred_transport"], "bus")
        self.assertEqual(kwargs["hotel_category"], "budget")

    @patch("app.services.ask_travel_router.optimize_budget")
    def test_route_travel_query_handles_comma_separated_budget_prompt(
        self,
        mock_optimize_budget
    ):
        mock_optimize_budget.return_value = {
            "budget_allocation": {"hotel": 10000, "transport": 8000}
        }

        result = route_travel_query(
            query=(
                "desitination is goa,2 traveller, trip days.5,"
                "budget is 50,000 .. optimise budget for me"
            ),
            role="user"
        )

        self.assertEqual(result["tool_used"], "budget_tool")
        kwargs = mock_optimize_budget.call_args.kwargs
        self.assertEqual(kwargs["destination"], "Goa")
        self.assertEqual(kwargs["total_budget"], 50000)
        self.assertEqual(kwargs["travelers"], 2)
        self.assertEqual(kwargs["trip_days"], 5)

    @patch("app.services.ask_travel_router.query_travel_assistant")
    def test_route_travel_query_uses_rag_for_non_itinerary_query(
        self,
        mock_query_travel_assistant
    ):
        mock_query_travel_assistant.return_value = {
            "query": "best beaches in goa",
            "answer": "Try Baga and Palolem.",
            "source": "rag_llm"
        }

        result = route_travel_query(
            query="best beaches in goa",
            role="user"
        )

        self.assertEqual(result["tool_used"], "rag_tool")
        mock_query_travel_assistant.assert_called_once()


if __name__ == "__main__":
    unittest.main()
