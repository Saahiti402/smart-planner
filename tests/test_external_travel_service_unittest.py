import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.services import external_travel_service as ets


class TestExternalTravelService(unittest.TestCase):

    def setUp(self):
        for cached_function in [
            ets._get_iata,
            ets._format_date,
            ets._fetch_flights_data,
            ets._fetch_hotels_data,
            ets._fetch_weather_data,
            ets._fetch_activities_data,
        ]:
            cached_function.cache_clear()

    @staticmethod
    def _invoke_router(query: str):
        router = ets.external_travel_tool
        if hasattr(router, "invoke"):
            return router.invoke(query)
        if hasattr(router, "func"):
            return router.func(query)
        return router(query)

    @staticmethod
    def _mock_response(status_code=200, json_data=None, text="ok"):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        response.json.return_value = json_data or {}
        return response

    def assertContainsAll(self, text, pieces):
        for piece in pieces:
            self.assertIn(piece, text)


def _add_test(name):
    def decorator(func):
        setattr(TestExternalTravelService, name, func)
        return func
    return decorator


def _make_simple_test(name, func):
    return _add_test(name)(func)


# -------------------------
# 10 IATA tests
# -------------------------

_make_simple_test(
    "test_get_iata_static_goa",
    lambda self: self.assertEqual(ets._get_iata("Goa"), "GOI"),
)
_make_simple_test(
    "test_get_iata_static_bengaluru_trimmed",
    lambda self: self.assertEqual(ets._get_iata(" bengaluru "), "BLR"),
)


@patch("app.services.external_travel_service.ask_groq_llm", return_value="JFK")
def _test_get_iata_llm_fallback(self, _mock_llm):
    self.assertEqual(ets._get_iata("Atlantis"), "JFK")


_add_test("test_get_iata_llm_fallback")(_test_get_iata_llm_fallback)


@patch("app.services.external_travel_service.ask_groq_llm", side_effect=Exception("boom"))
def _test_get_iata_llm_failure_falls_back_to_upper(self, mock_llm):
    self.assertEqual(ets._get_iata("Atlantis"), "ATLANTIS")


_add_test("test_get_iata_llm_failure_falls_back_to_upper")(_test_get_iata_llm_failure_falls_back_to_upper)


@patch("app.services.external_travel_service.ask_groq_llm", return_value="DXB")
def _test_get_iata_extracts_first_code(self, mock_llm):
    self.assertEqual(ets._get_iata("Dubai"), "DXB")


_add_test("test_get_iata_extracts_first_code")(_test_get_iata_extracts_first_code)


_make_simple_test(
    "test_get_iata_handles_whitespace_and_case",
    lambda self: self.assertEqual(ets._get_iata("  New York  "), "JFK"),
)


@patch("app.services.external_travel_service.ask_groq_llm", return_value="123")
def _test_get_iata_non_alpha_llm_output(self, mock_llm):
    self.assertEqual(ets._get_iata("Unknownopolis"), "UNKNOWNOPOLIS")


_add_test("test_get_iata_non_alpha_llm_output")(_test_get_iata_non_alpha_llm_output)


@patch("app.services.external_travel_service.ask_groq_llm", return_value="abc")
def _test_get_iata_lowercase_llm_code(self, mock_llm):
    self.assertEqual(ets._get_iata("Somewhere"), "ABC")


_add_test("test_get_iata_lowercase_llm_code")(_test_get_iata_lowercase_llm_code)


_make_simple_test(
    "test_get_iata_cache_hit_returns_same_value",
    lambda self: (
        self.assertEqual(ets._get_iata("Goa"), "GOI"),
        self.assertEqual(ets._get_iata("Goa"), "GOI"),
    ),
)


@patch("app.services.external_travel_service.ask_groq_llm", side_effect=Exception("boom"))
def _test_get_iata_unknown_city_uppercase_fallback(self, mock_llm):
    self.assertEqual(ets._get_iata("xanadu"), "XANADU")


_add_test("test_get_iata_unknown_city_uppercase_fallback")(_test_get_iata_unknown_city_uppercase_fallback)


# -------------------------
# 10 date-format tests
# -------------------------

_make_simple_test(
    "test_format_date_iso_passthrough",
    lambda self: self.assertEqual(ets._format_date("2026-07-19"), "2026-07-19"),
)
_make_simple_test(
    "test_format_date_empty_string",
    lambda self: self.assertEqual(ets._format_date(""), ""),
)
@patch("app.services.external_travel_service.ask_groq_llm", side_effect=Exception("bad llm"))
def _test_format_date_whitespace_string(self, mock_llm):
    self.assertEqual(ets._format_date("   "), "")


_add_test("test_format_date_whitespace_string")(_test_format_date_whitespace_string)


@patch("app.services.external_travel_service.ask_groq_llm", return_value="2026-08-15")
def _test_format_date_llm_returns_iso(self, mock_llm):
    self.assertEqual(ets._format_date("next independence day"), "2026-08-15")


_add_test("test_format_date_llm_returns_iso")(_test_format_date_llm_returns_iso)


@patch("app.services.external_travel_service.ask_groq_llm", return_value="August 15 2026")
def _test_format_date_llm_fallback_to_original(self, mock_llm):
    self.assertEqual(ets._format_date("unknown style"), "unknown style")


_add_test("test_format_date_llm_fallback_to_original")(_test_format_date_llm_fallback_to_original)


@patch("app.services.external_travel_service.ask_groq_llm", side_effect=Exception("bad llm"))
def _test_format_date_llm_exception_returns_original(self, mock_llm):
    self.assertEqual(ets._format_date("15/08/2026"), "15/08/2026")


_add_test("test_format_date_llm_exception_returns_original")(_test_format_date_llm_exception_returns_original)


@patch("app.services.external_travel_service.ask_groq_llm", side_effect=Exception("bad llm"))
def _test_format_date_negative_day_string_returns_original(self, mock_llm):
    self.assertEqual(ets._format_date("-1"), "-1")


_add_test("test_format_date_negative_day_string_returns_original")(_test_format_date_negative_day_string_returns_original)
_make_simple_test(
    "test_format_date_large_year_string_passthrough",
    lambda self: self.assertEqual(ets._format_date("9999-12-31"), "9999-12-31"),
)
_make_simple_test(
    "test_format_date_cache_hit",
    lambda self: (
        self.assertEqual(ets._format_date("2026-12-25"), "2026-12-25"),
        self.assertEqual(ets._format_date("2026-12-25"), "2026-12-25"),
    ),
)
_make_simple_test(
    "test_format_date_string_with_spaces_unchanged",
    lambda self: self.assertEqual(ets._format_date(" 2026-12-25 "), "2026-12-25"),
)
_make_simple_test(
    "test_format_date_today_string_passthrough",
    lambda self: self.assertEqual(ets._format_date(datetime.now().strftime("%Y-%m-%d")), datetime.now().strftime("%Y-%m-%d")),
)


# -------------------------
# 10 weather tests
# -------------------------


@patch("app.services.external_travel_service.requests.get")
def _test_weather_invalid_key(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=401, text="invalid key")
    self.assertIn("invalid or not activated", ets._fetch_weather_data("Goa"))


_add_test("test_weather_invalid_key")(_test_weather_invalid_key)


@patch("app.services.external_travel_service.requests.get")
def _test_weather_server_error(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=500, text="server error")
    self.assertIn("Weather API error: 500", ets._fetch_weather_data("Goa"))


_add_test("test_weather_server_error")(_test_weather_server_error)


@patch("app.services.external_travel_service.requests.get")
def _test_weather_empty_list(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"list": []})
    self.assertEqual(ets._fetch_weather_data("Goa"), "No weather data found for this city.")


_add_test("test_weather_empty_list")(_test_weather_empty_list)


@patch("app.services.external_travel_service.requests.get")
def _test_weather_one_forecast(self, mock_get):
    mock_get.return_value = self._mock_response(
        status_code=200,
        json_data={"list": [{"dt_txt": "2026-04-10 12:00:00", "main": {"temp": 29.5, "feels_like": 31.2}, "weather": [{"description": "light rain"}]}]},
    )
    output = ets._fetch_weather_data("Goa")
    self.assertContainsAll(output, ["Temp: 29.5°C", "Weather: light rain"])


_add_test("test_weather_one_forecast")(_test_weather_one_forecast)


@patch("app.services.external_travel_service.requests.get")
def _test_weather_multiple_forecasts(self, mock_get):
    mock_get.return_value = self._mock_response(
        status_code=200,
        json_data={
            "list": [
                {"dt_txt": "2026-04-10 09:00:00", "main": {"temp": 28.1, "feels_like": 30.0}, "weather": [{"description": "sunny"}]},
                {"dt_txt": "2026-04-10 12:00:00", "main": {"temp": 29.5, "feels_like": 31.2}, "weather": [{"description": "light rain"}]},
            ]
        },
    )
    output = ets._fetch_weather_data("Goa")
    self.assertContainsAll(output, ["Temp: 28.1°C", "Temp: 29.5°C", "sunny", "light rain"])


_add_test("test_weather_multiple_forecasts")(_test_weather_multiple_forecasts)


@patch("app.services.external_travel_service.requests.get")
def _test_weather_bad_json_shape(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"items": []})
    self.assertEqual(ets._fetch_weather_data("Goa"), "No weather data found for this city.")


_add_test("test_weather_bad_json_shape")(_test_weather_bad_json_shape)


@patch("app.services.external_travel_service.requests.get")
def _test_weather_request_exception(self, mock_get):
    mock_get.side_effect = Exception("network")
    self.assertIn("Weather fetch failed", ets._fetch_weather_data("Goa"))


_add_test("test_weather_request_exception")(_test_weather_request_exception)


@patch("app.services.external_travel_service.requests.get")
def _test_weather_long_city_name(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"list": [{"dt_txt": "2026-04-10 12:00:00", "main": {"temp": 25.0, "feels_like": 26.0}, "weather": [{"description": "clear sky"}]}]})
    output = ets._fetch_weather_data("x" * 256)
    self.assertIn("Temp: 25.0°C", output)


_add_test("test_weather_long_city_name")(_test_weather_long_city_name)


@patch("app.services.external_travel_service.requests.get")
def _test_weather_negative_temperature(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"list": [{"dt_txt": "2026-01-10 12:00:00", "main": {"temp": -5.5, "feels_like": -8.2}, "weather": [{"description": "snow"}]}]})
    output = ets._fetch_weather_data("Oslo")
    self.assertContainsAll(output, ["Temp: -5.5°C", "snow"])


_add_test("test_weather_negative_temperature")(_test_weather_negative_temperature)


@patch("app.services.external_travel_service.requests.get")
def _test_weather_cache_hit(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"list": [{"dt_txt": "2026-04-10 12:00:00", "main": {"temp": 29.5, "feels_like": 31.2}, "weather": [{"description": "light rain"}]}]})
    first = ets._fetch_weather_data("Goa")
    second = ets._fetch_weather_data("Goa")
    self.assertEqual(first, second)


_add_test("test_weather_cache_hit")(_test_weather_cache_hit)


# -------------------------
# 10 flights tests
# -------------------------


@patch("app.services.external_travel_service._format_date", side_effect=lambda value: value)
@patch("app.services.external_travel_service._get_iata", side_effect=["DEL", "BOM"])
@patch("app.services.external_travel_service.requests.get")
def _test_flights_success(self, mock_get, mock_iata, mock_date):
    mock_get.return_value = self._mock_response(
        status_code=200,
        json_data={"best_flights": [{"flights": [{"airline": "IndiGo", "departure_airport": {"name": "Delhi Airport"}, "arrival_airport": {"name": "Mumbai Airport"}}], "total_duration": 130, "price": 4500}]},
    )
    output = ets._fetch_flights_data("Delhi", "Mumbai", "2026-10-01")
    self.assertContainsAll(output, ["Airline: IndiGo (Direct)", "Price: ₹4500"])


_add_test("test_flights_success")(_test_flights_success)


@patch("app.services.external_travel_service._format_date", side_effect=lambda value: value)
@patch("app.services.external_travel_service._get_iata", side_effect=["DEL", "BOM", "DEL", "BOM"])
@patch("app.services.external_travel_service.requests.get")
def _test_flights_round_trip(self, mock_get, mock_iata, mock_date):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"best_flights": []})
    ets._fetch_flights_data("Delhi", "Mumbai", "2026-10-01", "2026-10-05")
    params = mock_get.call_args.kwargs["params"]
    self.assertEqual(params["type"], "1")
    self.assertEqual(params["return_date"], "2026-10-05")


_add_test("test_flights_round_trip")(_test_flights_round_trip)


@patch("app.services.external_travel_service._format_date", side_effect=lambda value: value)
@patch("app.services.external_travel_service._get_iata", side_effect=["DEL", "BOM"])
@patch("app.services.external_travel_service.requests.get")
def _test_flights_one_way(self, mock_get, mock_iata, mock_date):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"best_flights": []})
    ets._fetch_flights_data("Delhi", "Mumbai", "2026-10-01")
    self.assertEqual(mock_get.call_args.kwargs["params"]["type"], "2")


_add_test("test_flights_one_way")(_test_flights_one_way)


@patch("app.services.external_travel_service._format_date", side_effect=lambda value: value)
@patch("app.services.external_travel_service._get_iata", side_effect=Exception("iata fail"))
@patch("app.services.external_travel_service.requests.get")
def _test_flights_iata_failure(self, mock_get, mock_iata, mock_date):
    self.assertIn("Flights fetch failed", ets._fetch_flights_data("Delhi", "Mumbai", "2026-10-01"))


_add_test("test_flights_iata_failure")(_test_flights_iata_failure)


@patch("app.services.external_travel_service.requests.get")
def _test_flights_api_error_field(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"error": "bad query"})
    self.assertIn("Flights API error: bad query", ets._fetch_flights_data("Delhi", "Mumbai", "2026-10-01"))


_add_test("test_flights_api_error_field")(_test_flights_api_error_field)


@patch("app.services.external_travel_service.requests.get")
def _test_flights_no_results(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"best_flights": [], "other_flights": []})
    self.assertIn("No flights found", ets._fetch_flights_data("Delhi", "Mumbai", "2026-10-01"))


_add_test("test_flights_no_results")(_test_flights_no_results)


@patch("app.services.external_travel_service.requests.get")
def _test_flights_other_flights_fallback(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"best_flights": [], "other_flights": [{"flights": [{"airline": "Air India", "departure_airport": {"name": "Delhi"}, "arrival_airport": {"name": "Mumbai"}}], "total_duration": 150, "price": 6000}]})
    self.assertIn("Air India", ets._fetch_flights_data("Delhi", "Mumbai", "2026-10-01"))


_add_test("test_flights_other_flights_fallback")(_test_flights_other_flights_fallback)


@patch("app.services.external_travel_service.requests.get")
def _test_flights_request_exception(self, mock_get):
    mock_get.side_effect = Exception("network")
    self.assertIn("Flights fetch failed", ets._fetch_flights_data("Delhi", "Mumbai", "2026-10-01"))


_add_test("test_flights_request_exception")(_test_flights_request_exception)


@patch("app.services.external_travel_service.requests.get")
def _test_flights_three_results_limit(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={
        "best_flights": [
            {"flights": [{"airline": f"Air{i}", "departure_airport": {"name": "A"}, "arrival_airport": {"name": "B"}}], "total_duration": i * 10, "price": i * 1000}
            for i in range(1, 6)
        ]
    })
    output = ets._fetch_flights_data("Delhi", "Mumbai", "2026-10-01")
    self.assertIn("Air1", output)
    self.assertIn("Air3", output)
    self.assertNotIn("Air4", output)


_add_test("test_flights_three_results_limit")(_test_flights_three_results_limit)


@patch("app.services.external_travel_service.requests.get")
def _test_flights_missing_fields(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"best_flights": [{"flights": [{}], "total_duration": None, "price": None}]})
    output = ets._fetch_flights_data("Delhi", "Mumbai", "2026-10-01")
    self.assertIn("Airline: N/A", output)


_add_test("test_flights_missing_fields")(_test_flights_missing_fields)


# -------------------------
# 10 hotels/activities tests
# -------------------------


@patch.object(ets, "SERPAPI_KEY", None)
def _test_hotels_missing_key(self):
    self.assertEqual(ets._fetch_hotels_data("Goa", "2026-06-01", "2026-06-03"), "Error: SERPAPI_KEY missing.")


_add_test("test_hotels_missing_key")(_test_hotels_missing_key)


@patch.object(ets, "SERPAPI_KEY", "key")
@patch("app.services.external_travel_service.requests.get")
def _test_hotels_no_properties(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"properties": []})
    self.assertEqual(ets._fetch_hotels_data("Goa", "2026-06-01", "2026-06-03"), "No hotels found.")


_add_test("test_hotels_no_properties")(_test_hotels_no_properties)


@patch.object(ets, "SERPAPI_KEY", "key")
@patch("app.services.external_travel_service.requests.get")
def _test_hotels_three_results(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"properties": [
        {"name": "Hotel A", "rate_per_night": {"lowest": 3000}, "overall_rating": 4.5},
        {"name": "Hotel B", "rate_per_night": {"lowest": 4000}, "overall_rating": 4.8},
        {"name": "Hotel C", "rate_per_night": {"lowest": 5000}, "overall_rating": 4.2},
        {"name": "Hotel D", "rate_per_night": {"lowest": 6000}, "overall_rating": 4.9},
    ]})
    output = ets._fetch_hotels_data("Goa", "2026-06-01", "2026-06-03")
    self.assertContainsAll(output, ["Hotel A", "Hotel B", "Hotel C"])
    self.assertNotIn("Hotel D", output)


_add_test("test_hotels_three_results")(_test_hotels_three_results)


@patch.object(ets, "SERPAPI_KEY", "key")
@patch("app.services.external_travel_service.requests.get")
def _test_hotels_missing_fields(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"properties": [{"name": "Hotel X"}]})
    output = ets._fetch_hotels_data("Goa", "2026-06-01", "2026-06-03")
    self.assertContainsAll(output, ["Hotel X", "Unknown price", "No rating"])


_add_test("test_hotels_missing_fields")(_test_hotels_missing_fields)


@patch.object(ets, "SERPAPI_KEY", "key")
@patch("app.services.external_travel_service.requests.get")
def _test_hotels_request_exception(self, mock_get):
    mock_get.side_effect = Exception("network")
    self.assertIn("Error fetching hotels", ets._fetch_hotels_data("Goa", "2026-06-01", "2026-06-03"))


_add_test("test_hotels_request_exception")(_test_hotels_request_exception)


@patch.object(ets, "SERPAPI_KEY", "key")
@patch("app.services.external_travel_service._format_date", side_effect=lambda value: value)
@patch("app.services.external_travel_service.requests.get")
def _test_hotels_date_conversion(self, mock_get, mock_format_date):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"properties": []})
    ets._fetch_hotels_data("Goa", "next monday", "next tuesday")
    params = mock_get.call_args.kwargs["params"]
    self.assertEqual(params["check_in_date"], "next monday")
    self.assertEqual(params["check_out_date"], "next tuesday")


_add_test("test_hotels_date_conversion")(_test_hotels_date_conversion)


@patch.object(ets, "SERPAPI_KEY", "key")
@patch("app.services.external_travel_service.requests.get")
def _test_hotels_allows_large_city_names(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"properties": []})
    ets._fetch_hotels_data("x" * 200, "2026-06-01", "2026-06-03")
    self.assertEqual(mock_get.call_args.kwargs["params"]["q"], "x" * 200)


_add_test("test_hotels_allows_large_city_names")(_test_hotels_allows_large_city_names)


@patch.object(ets, "SERPAPI_KEY", "key")
@patch("app.services.external_travel_service.requests.get")
def _test_activities_missing_key(self, mock_get):
    with patch.object(ets, "SERPAPI_KEY", None):
        self.assertEqual(ets._fetch_activities_data("Paris"), "Error: SERPAPI_KEY missing.")


_add_test("test_activities_missing_key")(_test_activities_missing_key)


@patch.object(ets, "SERPAPI_KEY", "key")
@patch("app.services.external_travel_service.requests.get")
def _test_activities_no_results(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"local_results": []})
    self.assertEqual(ets._fetch_activities_data("Paris"), "No activities found.")


_add_test("test_activities_no_results")(_test_activities_no_results)


@patch.object(ets, "SERPAPI_KEY", "key")
@patch("app.services.external_travel_service.requests.get")
def _test_activities_two_results(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"local_results": [
        {"title": "Fort", "rating": 4.7, "address": "Center"},
        {"title": "Museum", "rating": 4.8, "address": "Old Town"},
    ]})
    output = ets._fetch_activities_data("Mysore")
    self.assertContainsAll(output, ["Fort", "Museum", "4.7", "4.8"])


_add_test("test_activities_two_results")(_test_activities_two_results)


@patch.object(ets, "SERPAPI_KEY", "key")
@patch("app.services.external_travel_service.requests.get")
def _test_activities_missing_fields(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"local_results": [{"title": "Fort"}]})
    output = ets._fetch_activities_data("Mysore")
    self.assertIn("Fort", output)


_add_test("test_activities_missing_fields")(_test_activities_missing_fields)


@patch.object(ets, "SERPAPI_KEY", "key")
@patch("app.services.external_travel_service.requests.get")
def _test_activities_request_exception(self, mock_get):
    mock_get.side_effect = Exception("network")
    self.assertIn("Error fetching activities", ets._fetch_activities_data("Mysore"))


_add_test("test_activities_request_exception")(_test_activities_request_exception)


@patch.object(ets, "SERPAPI_KEY", "key")
@patch("app.services.external_travel_service.requests.get")
def _test_activities_large_city_name(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"local_results": []})
    ets._fetch_activities_data("y" * 200)
    self.assertIn("y" * 200, mock_get.call_args.kwargs["params"]["q"])


_add_test("test_activities_large_city_name")(_test_activities_large_city_name)


@patch.object(ets, "SERPAPI_KEY", "key")
@patch("app.services.external_travel_service.requests.get")
def _test_activities_cache_hit(self, mock_get):
    mock_get.return_value = self._mock_response(status_code=200, json_data={"local_results": []})
    first = ets._fetch_activities_data("Paris")
    second = ets._fetch_activities_data("Paris")
    self.assertEqual(first, second)


_add_test("test_activities_cache_hit")(_test_activities_cache_hit)


# -------------------------
# 10 router tests
# -------------------------

@patch("app.services.external_travel_service._fetch_weather_data", return_value="weather ok")
def _test_router_routes_weather_queries(self, mock_weather):
    self.assertEqual(self._invoke_router("show weather in Goa"), "weather ok")


_add_test("test_router_routes_weather_queries")(_test_router_routes_weather_queries)


@patch("app.services.external_travel_service._fetch_flights_data", return_value="flights ok")
def _test_router_routes_flight_queries(self, mock_flights):
    self.assertEqual(self._invoke_router("find flights from Delhi to Mumbai"), "flights ok")


_add_test("test_router_routes_flight_queries")(_test_router_routes_flight_queries)


@patch("app.services.external_travel_service._fetch_hotels_data", return_value="hotels ok")
def _test_router_routes_hotel_queries(self, mock_hotels):
    self.assertEqual(self._invoke_router("show hotel options in Goa"), "hotels ok")


_add_test("test_router_routes_hotel_queries")(_test_router_routes_hotel_queries)


@patch("app.services.external_travel_service._fetch_activities_data", return_value="activities ok")
def _test_router_routes_activity_queries(self, mock_activities):
    self.assertEqual(self._invoke_router("things to do in Mysore"), "activities ok")


_add_test("test_router_routes_activity_queries")(_test_router_routes_activity_queries)
_make_simple_test(
    "test_router_unknown_query_help",
    lambda self: self.assertIn("Please specify", self._invoke_router("tell me something random")),
)
_make_simple_test(
    "test_router_empty_query_help",
    lambda self: self.assertIn("Please specify", self._invoke_router("")),
)
_make_simple_test(
    "test_router_planned_keyword_uses_hotel_or_trip_path",
    lambda self: self.assertIn("Please specify", self._invoke_router("planned trip in Goa")),
)


@patch("app.services.external_travel_service._fetch_weather_data", return_value="weather ok")
def _test_router_current_keyword_with_weather_context(self, mock_weather):
    self.assertEqual(self._invoke_router("current weather in Goa"), "weather ok")


_add_test("test_router_current_keyword_with_weather_context")(_test_router_current_keyword_with_weather_context)


@patch("app.services.external_travel_service._fetch_weather_data", return_value="weather ok")
def _test_router_query_case_insensitive(self, mock_weather):
    self.assertEqual(self._invoke_router("WEATHER IN GOA"), "weather ok")


_add_test("test_router_query_case_insensitive")(_test_router_query_case_insensitive)
_make_simple_test(
    "test_router_whitespace_query_help",
    lambda self: self.assertIn("Please specify", self._invoke_router("   ")),
)


if __name__ == "__main__":
    unittest.main()
