import unittest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestTripAPI(unittest.TestCase):

    def setUp(self):
        self.user_id = "796773ab-dcad-4c19-b973-00415e08e8ab"

    def test_create_trip_valid(self):
        payload = {
            "user_id": self.user_id,
            "source": "Chennai",
            "destination": "Mysore",
            "start_date": "2026-06-01",
            "end_date": "2026-06-03",
            "budget": 12000,
            "travelers": 1
        }
        response = client.post("/trip", json=payload)
        self.assertEqual(response.status_code, 200)

    def test_missing_field(self):
        payload = {
            "user_id": self.user_id,
            "destination": "Coorg"
        }
        response = client.post("/trip", json=payload)
        self.assertNotEqual(response.status_code, 200)

    def test_invalid_date_format(self):
        payload = {
            "user_id": self.user_id,
            "source": "Pune",
            "destination": "Goa",
            "start_date": "10-07-2026",
            "end_date": "15-07-2026",
            "budget": 20000,
            "travelers": 2
        }
        response = client.post("/trip", json=payload)
        self.assertNotEqual(response.status_code, 200)

    def test_invalid_date_range(self):
        payload = {
            "user_id": self.user_id,
            "source": "Kolkata",
            "destination": "Delhi",
            "start_date": "2026-09-10",
            "end_date": "2026-09-05",
            "budget": 18000,
            "travelers": 2
        }
        response = client.post("/trip", json=payload)
        self.assertNotEqual(response.status_code, 200)

    def test_negative_budget(self):
        payload = {
            "user_id": self.user_id,
            "source": "Ahmedabad",
            "destination": "Jaipur",
            "start_date": "2026-10-01",
            "end_date": "2026-10-03",
            "budget": -5000,
            "travelers": 2
        }
        response = client.post("/trip", json=payload)
        self.assertNotEqual(response.status_code, 200)

    def test_zero_travelers(self):
        payload = {
            "user_id": self.user_id,
            "source": "Surat",
            "destination": "Udaipur",
            "start_date": "2026-11-01",
            "end_date": "2026-11-04",
            "budget": 10000,
            "travelers": 0
        }
        response = client.post("/trip", json=payload)
        self.assertNotEqual(response.status_code, 200)

    def test_same_day_trip(self):
        payload = {
            "user_id": self.user_id,
            "source": "Bhopal",
            "destination": "Indore",
            "start_date": "2026-12-01",
            "end_date": "2026-12-01",
            "budget": 3000,
            "travelers": 1
        }
        response = client.post("/trip", json=payload)
        self.assertEqual(response.status_code, 200)

    def test_large_budget(self):
        payload = {
            "user_id": self.user_id,
            "source": "Lucknow",
            "destination": "Varanasi",
            "start_date": "2027-01-10",
            "end_date": "2027-01-15",
            "budget": 99999999,
            "travelers": 4
        }
        response = client.post("/trip", json=payload)
        self.assertEqual(response.status_code, 200)

    def test_invalid_user_id(self):
        response = client.get("/trips/invalid-id")
        self.assertNotEqual(response.status_code, 200)

    def test_get_trips(self):
        response = client.get(f"/trips/{self.user_id}")
        self.assertEqual(response.status_code, 200)

    def test_no_trips_user(self):
        response = client.get("/trips/00000000-0000-0000-0000-000000000000")
        self.assertEqual(response.status_code, 200)

    def test_query_past(self):
        payload = {"user_id": self.user_id, "query": "past trips"}
        response = client.post("/trip/query", json=payload)
        self.assertEqual(response.status_code, 200)

    def test_query_current(self):
        payload = {"user_id": self.user_id, "query": "current trip"}
        response = client.post("/trip/query", json=payload)
        self.assertEqual(response.status_code, 200)

    def test_query_planned(self):
        payload = {"user_id": self.user_id, "query": "next trip"}
        response = client.post("/trip/query", json=payload)
        self.assertEqual(response.status_code, 200)

    def test_query_unknown(self):
        payload = {"user_id": self.user_id, "query": "random text"}
        response = client.post("/trip/query", json=payload)
        self.assertEqual(response.status_code, 200)

    # 🔥 NEW ADVANCED TESTS

    def test_empty_query(self):
        payload = {"user_id": self.user_id, "query": ""}
        response = client.post("/trip/query", json=payload)
        self.assertEqual(response.status_code, 200)

    def test_case_insensitive_query(self):
        payload = {"user_id": self.user_id, "query": "PAST TRIPS"}
        response = client.post("/trip/query", json=payload)
        self.assertEqual(response.status_code, 200)

    def test_query_specific_destination(self):
        payload = {"user_id": self.user_id, "query": "goa trip"}
        response = client.post("/trip/query", json=payload)
        self.assertEqual(response.status_code, 200)

    def test_create_trip_min_budget(self):
        payload = {
            "user_id": self.user_id,
            "source": "Delhi",
            "destination": "Agra",
            "start_date": "2026-05-01",
            "end_date": "2026-05-02",
            "budget": 1,
            "travelers": 1
        }
        response = client.post("/trip", json=payload)
        self.assertEqual(response.status_code, 200)

    def test_create_trip_large_travelers(self):
        payload = {
            "user_id": self.user_id,
            "source": "Mumbai",
            "destination": "Goa",
            "start_date": "2026-05-10",
            "end_date": "2026-05-15",
            "budget": 50000,
            "travelers": 50
        }
        response = client.post("/trip", json=payload)
        self.assertEqual(response.status_code, 200)

    def test_create_trip_empty_strings(self):
        payload = {
            "user_id": self.user_id,
            "source": "",
            "destination": "",
            "start_date": "2026-06-01",
            "end_date": "2026-06-02",
            "budget": 10000,
            "travelers": 1
        }
        response = client.post("/trip", json=payload)
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()