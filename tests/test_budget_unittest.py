import unittest
from app.services.budget_service import optimize_budget
from fastapi import HTTPException


class TestBudgetOptimizer(unittest.TestCase):

    def test_valid_budget(self):
        result = optimize_budget("Goa", 50000, 2, 4)
        self.assertIn("budget_allocation", result)

    def test_allocation_sum(self):
        result = optimize_budget("Goa", 50000, 2, 4)
        total = sum(result["budget_allocation"].values())
        self.assertAlmostEqual(total, 50000, delta=10)

    def test_low_budget(self):
        result = optimize_budget("Goa", 1000, 2, 5)
        self.assertIn("error", result)

    def test_exact_min_budget(self):
        result = optimize_budget("Goa", 10000, 2, 5)
        self.assertNotIn("error", result)

    def test_per_person_budget(self):
        result = optimize_budget("Kerala", 40000, 4, 4)
        self.assertEqual(result["per_person_budget"], 10000)

    def test_short_trip(self):
        result = optimize_budget("Goa", 30000, 2, 2)
        self.assertIn("budget_allocation", result)

    def test_long_trip(self):
        result = optimize_budget("Goa", 70000, 2, 7)
        self.assertIn("budget_allocation", result)

    def test_budget_hotel(self):
        result = optimize_budget("Goa", 30000, 2, 4, hotel_category="budget")
        self.assertIn("budget_allocation", result)

    def test_luxury_hotel(self):
        result = optimize_budget("Goa", 100000, 2, 4, hotel_category="5-star")
        self.assertEqual(result["recommended_transport"], "flight")

    def test_transport_flight(self):
        result = optimize_budget("Goa", 50000, 2, 4, preferred_transport="flight")
        self.assertEqual(result["recommended_transport"], "flight")

    def test_transport_bus(self):
        result = optimize_budget("Goa", 30000, 2, 4, preferred_transport="bus")
        self.assertEqual(result["recommended_transport"], "bus")

    def test_low_budget_recommendation(self):
        result = optimize_budget("Goa", 15000, 2, 3)
        self.assertEqual(result["recommended_hotel"], "budget hotel / hostel")

    def test_mid_budget_recommendation(self):
        result = optimize_budget("Goa", 40000, 2, 3)
        self.assertEqual(result["recommended_hotel"], "3-star hotel")

    def test_high_budget_recommendation(self):
        result = optimize_budget("Goa", 100000, 2, 3)
        self.assertEqual(result["recommended_transport"], "flight")

    def test_invalid_budget(self):
        with self.assertRaises(HTTPException):
            optimize_budget("Goa", -1000, 2, 3)

    def test_zero_travelers(self):
        with self.assertRaises(HTTPException):
            optimize_budget("Goa", 20000, 0, 3)

    def test_zero_trip_days(self):
        with self.assertRaises(HTTPException):
            optimize_budget("Goa", 20000, 2, 0)

    def test_single_traveler(self):
        result = optimize_budget("Goa", 20000, 1, 2)
        self.assertEqual(result["per_person_budget"], 20000)

    def test_many_travelers(self):
        result = optimize_budget("Goa", 100000, 10, 2)
        self.assertEqual(result["per_person_budget"], 10000)

    def test_case_insensitive_hotel(self):
        result = optimize_budget("Goa", 30000, 2, 3, hotel_category="BUDGET")
        self.assertIn("budget_allocation", result)

    def test_train_transport(self):
        result = optimize_budget("Goa", 30000, 2, 3, preferred_transport="train")
        self.assertEqual(result["recommended_transport"], "train")

    def test_large_budget(self):
        result = optimize_budget("Goa", 1000000, 5, 10)
        self.assertIn("budget_allocation", result)

    def test_allocation_keys(self):
        result = optimize_budget("Goa", 50000, 2, 3)
        keys = result["budget_allocation"].keys()
        self.assertCountEqual(keys, ["hotel", "transport", "food", "activities", "misc"])


if __name__ == "__main__":
    unittest.main()