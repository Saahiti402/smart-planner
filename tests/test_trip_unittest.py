import unittest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestTripAPI(unittest.TestCase):

    def setUp(self):
        self.user_id = "ad770edd-70c0-4977-a0dd-f2a2448c1bc4"

    # -------------------------
    # TEST CREATE TRIP
    # -------------------------
    def test_create_trip(self):
        payload = {
            "user_id": self.user_id,
            "source": "Mumbai",
            "destination": "Bangalore",
            "start_date": "2026-05-01",
            "end_date": "2026-05-03",
            "budget": 25000,
            "travelers": 5
        }

        response = client.post("/trip", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertIn("trip_id", response.json())

    # -------------------------
    # TEST GET TRIPS
    # -------------------------
    def test_get_trips(self):
        response = client.get(f"/trips/{self.user_id}")

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    # -------------------------
    # TEST QUERY TRIPS
    # -------------------------
    def test_query_trips(self):
        payload = {
            "user_id": self.user_id,
            "query": "last goa trip budget"
        }

        response = client.post("/trip/query", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertIn("answer", response.json())

    # -------------------------
    # TEST NO TRIPS CASE
    # -------------------------
    def test_no_trips(self):
        payload = {
            "user_id": "00000000-0000-0000-0000-000000000000",
            "query": "show my past trips"
        }

        response = client.post("/trip/query", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "No trips found")


if __name__ == "__main__":
    unittest.main()