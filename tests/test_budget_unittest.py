import unittest
import sys
import os

# add project root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.budget_service import optimize_budget


class TestBudgetOptimizer(unittest.TestCase):

    def test_valid_budget(self):

        result = optimize_budget(
            destination="Goa",
            total_budget=50000,
            travelers=2,
            trip_days=4
        )

        self.assertIn("budget_allocation", result)

        total_allocated = sum(result["budget_allocation"].values())

        self.assertAlmostEqual(total_allocated, 50000, delta=10)


    def test_low_budget(self):

        result = optimize_budget(
            destination="Goa",
            total_budget=1000,
            travelers=2,
            trip_days=5
        )

        self.assertIn("error", result)


    def test_per_person_budget(self):

        result = optimize_budget(
            destination="Kerala",
            total_budget=40000,
            travelers=4,
            trip_days=4
        )

        self.assertEqual(result["per_person_budget"], 10000)


if __name__ == "__main__":
    unittest.main()
