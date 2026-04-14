import unittest
from datetime import datetime as real_datetime
from unittest.mock import MagicMock, patch

from app.services import destination_compare_service as dcs


class TestDestinationCompareService(unittest.TestCase):

    def _mock_path(self, text: str, exists: bool = True):
        path = MagicMock()
        path.exists.return_value = exists
        path.read_text.return_value = text
        return path


def _add_test(name):
    def decorator(func):
        setattr(TestDestinationCompareService, name, func)
        return func
    return decorator


# -------------------------
# 15 _parse_destinations tests
# -------------------------


@patch.object(dcs, "DESTINATIONS_FILE")
def _test_parse_destinations_file_missing(self, mock_file):
    mock_file.exists.return_value = False
    self.assertEqual(dcs._parse_destinations(), [])


_add_test("test_parse_destinations_file_missing")(_test_parse_destinations_file_missing)


@patch.object(dcs, "DESTINATIONS_FILE")
def _test_parse_destinations_empty_file(self, mock_file):
    mock_file.exists.return_value = True
    mock_file.read_text.return_value = ""
    self.assertEqual(dcs._parse_destinations(), [])


_add_test("test_parse_destinations_empty_file")(_test_parse_destinations_empty_file)


@patch.object(dcs, "DESTINATIONS_FILE")
def _test_parse_destinations_single_city_full_sections(self, mock_file):
    mock_file.exists.return_value = True
    mock_file.read_text.return_value = """
=== CITY: Goa ===
Overview:
Beach paradise
Best Time to Visit:
Nov to Feb
Popular Attractions:
- Baga Beach
- Fort Aguada
Suggested Itinerary:
- Day 1: Beaches
Food Recommendations:
- Prawn Curry
"""
    parsed = dcs._parse_destinations()
    self.assertEqual(len(parsed), 1)
    self.assertEqual(parsed[0]["name"], "Goa")
    self.assertEqual(parsed[0]["slug"], "goa")
    self.assertEqual(parsed[0]["overview"], "Beach paradise")
    self.assertEqual(parsed[0]["best_time"], "Nov to Feb")
    self.assertEqual(parsed[0]["popular_attractions"], ["Baga Beach", "Fort Aguada"])


_add_test("test_parse_destinations_single_city_full_sections")(_test_parse_destinations_single_city_full_sections)


@patch.object(dcs, "DESTINATIONS_FILE")
def _test_parse_destinations_multiple_cities(self, mock_file):
    mock_file.exists.return_value = True
    mock_file.read_text.return_value = """
=== CITY: Goa ===
Overview:
Nice
=== CITY: Mysore ===
Overview:
Royal city
"""
    parsed = dcs._parse_destinations()
    self.assertEqual([entry["name"] for entry in parsed], ["Goa", "Mysore"])


_add_test("test_parse_destinations_multiple_cities")(_test_parse_destinations_multiple_cities)


@patch.object(dcs, "DESTINATIONS_FILE")
def _test_parse_destinations_ignores_lines_before_first_city(self, mock_file):
    mock_file.exists.return_value = True
    mock_file.read_text.return_value = """
Some intro line
Another line
=== CITY: Goa ===
Overview:
Sea side
"""
    parsed = dcs._parse_destinations()
    self.assertEqual(len(parsed), 1)
    self.assertEqual(parsed[0]["name"], "Goa")


_add_test("test_parse_destinations_ignores_lines_before_first_city")(_test_parse_destinations_ignores_lines_before_first_city)


@patch.object(dcs, "DESTINATIONS_FILE")
def _test_parse_destinations_unknown_section_is_ignored(self, mock_file):
    mock_file.exists.return_value = True
    mock_file.read_text.return_value = """
=== CITY: Goa ===
Unknown Section:
Whatever
Overview:
Known
"""
    parsed = dcs._parse_destinations()
    self.assertEqual(parsed[0]["overview"], "Known")


_add_test("test_parse_destinations_unknown_section_is_ignored")(_test_parse_destinations_unknown_section_is_ignored)


@patch.object(dcs, "DESTINATIONS_FILE")
def _test_parse_destinations_city_name_title_cased(self, mock_file):
    mock_file.exists.return_value = True
    mock_file.read_text.return_value = "=== CITY: mYsOre ===\nOverview:\nGreat"
    parsed = dcs._parse_destinations()
    self.assertEqual(parsed[0]["name"], "Mysore")


_add_test("test_parse_destinations_city_name_title_cased")(_test_parse_destinations_city_name_title_cased)


@patch.object(dcs, "DESTINATIONS_FILE")
def _test_parse_destinations_slug_spaces_to_hyphen(self, mock_file):
    mock_file.exists.return_value = True
    mock_file.read_text.return_value = "=== CITY: New York ===\nOverview:\nBig"
    parsed = dcs._parse_destinations()
    self.assertEqual(parsed[0]["slug"], "new-york")


_add_test("test_parse_destinations_slug_spaces_to_hyphen")(_test_parse_destinations_slug_spaces_to_hyphen)


@patch.object(dcs, "DESTINATIONS_FILE")
def _test_parse_destinations_list_lines_strip_dash_and_space(self, mock_file):
    mock_file.exists.return_value = True
    mock_file.read_text.return_value = """
=== CITY: Goa ===
Popular Attractions:
-  Baga
-Fort
"""
    parsed = dcs._parse_destinations()
    self.assertEqual(parsed[0]["popular_attractions"], ["Baga", "Fort"])


_add_test("test_parse_destinations_list_lines_strip_dash_and_space")(_test_parse_destinations_list_lines_strip_dash_and_space)


@patch.object(dcs, "DESTINATIONS_FILE")
def _test_parse_destinations_list_lines_without_dash_kept(self, mock_file):
    mock_file.exists.return_value = True
    mock_file.read_text.return_value = """
=== CITY: Goa ===
Popular Attractions:
Museum
"""
    parsed = dcs._parse_destinations()
    self.assertEqual(parsed[0]["popular_attractions"], ["Museum"])


_add_test("test_parse_destinations_list_lines_without_dash_kept")(_test_parse_destinations_list_lines_without_dash_kept)


@patch.object(dcs, "DESTINATIONS_FILE")
def _test_parse_destinations_blank_lines_ignored(self, mock_file):
    mock_file.exists.return_value = True
    mock_file.read_text.return_value = """

=== CITY: Goa ===

Overview:

Clean

"""
    parsed = dcs._parse_destinations()
    self.assertEqual(parsed[0]["overview"], "Clean")


_add_test("test_parse_destinations_blank_lines_ignored")(_test_parse_destinations_blank_lines_ignored)


@patch.object(dcs, "DESTINATIONS_FILE")
def _test_parse_destinations_scalar_section_overwrites_previous_line(self, mock_file):
    mock_file.exists.return_value = True
    mock_file.read_text.return_value = """
=== CITY: Goa ===
Overview:
Line one
Line two
"""
    parsed = dcs._parse_destinations()
    self.assertEqual(parsed[0]["overview"], "Line two")


_add_test("test_parse_destinations_scalar_section_overwrites_previous_line")(_test_parse_destinations_scalar_section_overwrites_previous_line)


@patch.object(dcs, "DESTINATIONS_FILE")
def _test_parse_destinations_city_with_no_sections_defaults(self, mock_file):
    mock_file.exists.return_value = True
    mock_file.read_text.return_value = "=== CITY: Goa ==="
    parsed = dcs._parse_destinations()
    self.assertEqual(parsed[0]["overview"], "")
    self.assertEqual(parsed[0]["popular_attractions"], [])


_add_test("test_parse_destinations_city_with_no_sections_defaults")(_test_parse_destinations_city_with_no_sections_defaults)


@patch.object(dcs, "DESTINATIONS_FILE")
def _test_parse_destinations_trailing_city_is_appended(self, mock_file):
    mock_file.exists.return_value = True
    mock_file.read_text.return_value = "=== CITY: Goa ===\nOverview:\nOne"
    parsed = dcs._parse_destinations()
    self.assertEqual(len(parsed), 1)


_add_test("test_parse_destinations_trailing_city_is_appended")(_test_parse_destinations_trailing_city_is_appended)


@patch.object(dcs, "DESTINATIONS_FILE")
def _test_parse_destinations_malformed_city_header_ignored(self, mock_file):
    mock_file.exists.return_value = True
    mock_file.read_text.return_value = "=== CITY: Goa\nOverview:\nNot parsed"
    self.assertEqual(dcs._parse_destinations(), [])


_add_test("test_parse_destinations_malformed_city_header_ignored")(_test_parse_destinations_malformed_city_header_ignored)


# -------------------------
# 10 _parse_city_blocks tests
# -------------------------


def _city_block_path(text: str, exists: bool = True):
    path = MagicMock()
    path.exists.return_value = exists
    path.read_text.return_value = text
    return path


def _test_parse_city_blocks_missing_file(self):
    self.assertEqual(dcs._parse_city_blocks(_city_block_path("", exists=False)), {})


_add_test("test_parse_city_blocks_missing_file")(_test_parse_city_blocks_missing_file)


def _test_parse_city_blocks_empty_file(self):
    self.assertEqual(dcs._parse_city_blocks(_city_block_path("", exists=True)), {})


_add_test("test_parse_city_blocks_empty_file")(_test_parse_city_blocks_empty_file)


def _test_parse_city_blocks_single_city(self):
    path = _city_block_path("=== CITY: Goa ===\nLine A\nLine B")
    parsed = dcs._parse_city_blocks(path)
    self.assertEqual(parsed["Goa"], ["Line A", "Line B"])


_add_test("test_parse_city_blocks_single_city")(_test_parse_city_blocks_single_city)


def _test_parse_city_blocks_multiple_cities(self):
    path = _city_block_path("=== CITY: Goa ===\nA\n=== CITY: Mysore ===\nB")
    parsed = dcs._parse_city_blocks(path)
    self.assertEqual(parsed["Goa"], ["A"])
    self.assertEqual(parsed["Mysore"], ["B"])


_add_test("test_parse_city_blocks_multiple_cities")(_test_parse_city_blocks_multiple_cities)


def _test_parse_city_blocks_ignores_text_before_first_city(self):
    path = _city_block_path("Intro\n=== CITY: Goa ===\nA")
    parsed = dcs._parse_city_blocks(path)
    self.assertEqual(parsed["Goa"], ["A"])


_add_test("test_parse_city_blocks_ignores_text_before_first_city")(_test_parse_city_blocks_ignores_text_before_first_city)


def _test_parse_city_blocks_strips_whitespace_lines(self):
    path = _city_block_path("=== CITY: Goa ===\n  A  \n\n  B")
    parsed = dcs._parse_city_blocks(path)
    self.assertEqual(parsed["Goa"], ["A", "B"])


_add_test("test_parse_city_blocks_strips_whitespace_lines")(_test_parse_city_blocks_strips_whitespace_lines)


def _test_parse_city_blocks_city_name_title_case(self):
    path = _city_block_path("=== CITY: mYsOre ===\nLine")
    parsed = dcs._parse_city_blocks(path)
    self.assertIn("Mysore", parsed)


_add_test("test_parse_city_blocks_city_name_title_case")(_test_parse_city_blocks_city_name_title_case)


def _test_parse_city_blocks_last_city_appended(self):
    path = _city_block_path("=== CITY: Goa ===\nLast")
    parsed = dcs._parse_city_blocks(path)
    self.assertEqual(len(parsed), 1)


_add_test("test_parse_city_blocks_last_city_appended")(_test_parse_city_blocks_last_city_appended)


def _test_parse_city_blocks_malformed_header_treated_as_content(self):
    path = _city_block_path("=== CITY: Goa ===\n=== CITY: bad\nLine")
    parsed = dcs._parse_city_blocks(path)
    self.assertIn("=== CITY: bad", parsed["Goa"])


_add_test("test_parse_city_blocks_malformed_header_treated_as_content")(_test_parse_city_blocks_malformed_header_treated_as_content)


def _test_parse_city_blocks_duplicate_city_keeps_latest_block(self):
    path = _city_block_path("=== CITY: Goa ===\nA\n=== CITY: Goa ===\nB")
    parsed = dcs._parse_city_blocks(path)
    self.assertEqual(parsed["Goa"], ["B"])


_add_test("test_parse_city_blocks_duplicate_city_keeps_latest_block")(_test_parse_city_blocks_duplicate_city_keeps_latest_block)


# -------------------------
# 8 _extract_pricing tests
# -------------------------


@patch("app.services.destination_compare_service._parse_city_blocks", return_value={})
def _test_extract_pricing_city_missing(self, _mock_blocks):
    self.assertEqual(dcs._extract_pricing("Goa"), {"public_pricing": []})


_add_test("test_extract_pricing_city_missing")(_test_extract_pricing_city_missing)


@patch("app.services.destination_compare_service._parse_city_blocks")
def _test_extract_pricing_collects_public_only(self, mock_blocks):
    mock_blocks.return_value = {
        "Goa": [
            "Public Pricing:",
            "- ₹1000/day",
            "Internal Pricing (ADMIN ONLY):",
            "- Secret",
        ]
    }
    self.assertEqual(dcs._extract_pricing("Goa")["public_pricing"], ["₹1000/day"])


_add_test("test_extract_pricing_collects_public_only")(_test_extract_pricing_collects_public_only)


@patch("app.services.destination_compare_service._parse_city_blocks")
def _test_extract_pricing_no_public_header(self, mock_blocks):
    mock_blocks.return_value = {"Goa": ["- ₹1000/day"]}
    self.assertEqual(dcs._extract_pricing("Goa")["public_pricing"], [])


_add_test("test_extract_pricing_no_public_header")(_test_extract_pricing_no_public_header)


@patch("app.services.destination_compare_service._parse_city_blocks")
def _test_extract_pricing_mixed_bullet_formats(self, mock_blocks):
    mock_blocks.return_value = {"Goa": ["Public Pricing:", "-One", "- Two", "Three"]}
    self.assertEqual(dcs._extract_pricing("Goa")["public_pricing"], ["One", "Two", "Three"])


_add_test("test_extract_pricing_mixed_bullet_formats")(_test_extract_pricing_mixed_bullet_formats)


@patch("app.services.destination_compare_service._parse_city_blocks")
def _test_extract_pricing_order_preserved(self, mock_blocks):
    mock_blocks.return_value = {"Goa": ["Public Pricing:", "- First", "- Second"]}
    self.assertEqual(dcs._extract_pricing("Goa")["public_pricing"], ["First", "Second"])


_add_test("test_extract_pricing_order_preserved")(_test_extract_pricing_order_preserved)


@patch("app.services.destination_compare_service._parse_city_blocks")
def _test_extract_pricing_internal_section_not_included(self, mock_blocks):
    mock_blocks.return_value = {
        "Goa": ["Public Pricing:", "- Public", "Internal Pricing (ADMIN ONLY):", "- Internal"]
    }
    self.assertNotIn("Internal", dcs._extract_pricing("Goa")["public_pricing"])


_add_test("test_extract_pricing_internal_section_not_included")(_test_extract_pricing_internal_section_not_included)


@patch("app.services.destination_compare_service._parse_city_blocks")
def _test_extract_pricing_extreme_long_text(self, mock_blocks):
    long_text = "₹" + ("9" * 5000)
    mock_blocks.return_value = {"Goa": ["Public Pricing:", f"- {long_text}"]}
    self.assertEqual(dcs._extract_pricing("Goa")["public_pricing"], [long_text])


_add_test("test_extract_pricing_extreme_long_text")(_test_extract_pricing_extreme_long_text)


@patch("app.services.destination_compare_service._parse_city_blocks")
def _test_extract_pricing_unknown_city_returns_empty(self, mock_blocks):
    mock_blocks.return_value = {"Mysore": ["Public Pricing:", "- 100"]}
    self.assertEqual(dcs._extract_pricing("Goa")["public_pricing"], [])


_add_test("test_extract_pricing_unknown_city_returns_empty")(_test_extract_pricing_unknown_city_returns_empty)


# -------------------------
# 8 _extract_hotel_pricing tests
# -------------------------


@patch("app.services.destination_compare_service._parse_city_blocks", return_value={})
def _test_extract_hotel_pricing_city_missing(self, _mock_blocks):
    self.assertEqual(dcs._extract_hotel_pricing("Goa"), {"hotel_options": []})


_add_test("test_extract_hotel_pricing_city_missing")(_test_extract_hotel_pricing_city_missing)


@patch("app.services.destination_compare_service._parse_city_blocks")
def _test_extract_hotel_pricing_skips_hotels_header(self, mock_blocks):
    mock_blocks.return_value = {"Goa": ["Hotels:", "- A"]}
    self.assertEqual(dcs._extract_hotel_pricing("Goa")["hotel_options"], ["A"])


_add_test("test_extract_hotel_pricing_skips_hotels_header")(_test_extract_hotel_pricing_skips_hotels_header)


@patch("app.services.destination_compare_service._parse_city_blocks")
def _test_extract_hotel_pricing_skips_checkin_line(self, mock_blocks):
    mock_blocks.return_value = {"Goa": ["Check-in: 2026-01-01", "- A"]}
    self.assertEqual(dcs._extract_hotel_pricing("Goa")["hotel_options"], ["A"])


_add_test("test_extract_hotel_pricing_skips_checkin_line")(_test_extract_hotel_pricing_skips_checkin_line)


@patch("app.services.destination_compare_service._parse_city_blocks")
def _test_extract_hotel_pricing_skips_checkout_line(self, mock_blocks):
    mock_blocks.return_value = {"Goa": ["Check-out: 2026-01-03", "- A"]}
    self.assertEqual(dcs._extract_hotel_pricing("Goa")["hotel_options"], ["A"])


_add_test("test_extract_hotel_pricing_skips_checkout_line")(_test_extract_hotel_pricing_skips_checkout_line)


@patch("app.services.destination_compare_service._parse_city_blocks")
def _test_extract_hotel_pricing_strips_dash_prefix(self, mock_blocks):
    mock_blocks.return_value = {"Goa": ["-  Hotel X"]}
    self.assertEqual(dcs._extract_hotel_pricing("Goa")["hotel_options"], ["Hotel X"])


_add_test("test_extract_hotel_pricing_strips_dash_prefix")(_test_extract_hotel_pricing_strips_dash_prefix)


@patch("app.services.destination_compare_service._parse_city_blocks")
def _test_extract_hotel_pricing_preserves_order(self, mock_blocks):
    mock_blocks.return_value = {"Goa": ["- A", "- B", "- C"]}
    self.assertEqual(dcs._extract_hotel_pricing("Goa")["hotel_options"], ["A", "B", "C"])


_add_test("test_extract_hotel_pricing_preserves_order")(_test_extract_hotel_pricing_preserves_order)


@patch("app.services.destination_compare_service._parse_city_blocks")
def _test_extract_hotel_pricing_unicode_values(self, mock_blocks):
    mock_blocks.return_value = {"Goa": ["- Hôtel Étoile ⭐"]}
    self.assertEqual(dcs._extract_hotel_pricing("Goa")["hotel_options"], ["Hôtel Étoile ⭐"])


_add_test("test_extract_hotel_pricing_unicode_values")(_test_extract_hotel_pricing_unicode_values)


@patch("app.services.destination_compare_service._parse_city_blocks")
def _test_extract_hotel_pricing_extreme_long_name(self, mock_blocks):
    long_name = "Hotel-" + ("X" * 3000)
    mock_blocks.return_value = {"Goa": [f"- {long_name}"]}
    self.assertEqual(dcs._extract_hotel_pricing("Goa")["hotel_options"], [long_name])


_add_test("test_extract_hotel_pricing_extreme_long_name")(_test_extract_hotel_pricing_extreme_long_name)


# -------------------------
# 8 list_destinations tests
# -------------------------


@patch("app.services.destination_compare_service._parse_destinations", return_value=[])
def _test_list_destinations_empty(self, _mock_parse):
    self.assertEqual(dcs.list_destinations(), [])


_add_test("test_list_destinations_empty")(_test_list_destinations_empty)


@patch("app.services.destination_compare_service._extract_pricing")
@patch("app.services.destination_compare_service._parse_destinations")
def _test_list_destinations_basic_mapping(self, mock_parse, mock_pricing):
    mock_parse.return_value = [{
        "name": "Goa",
        "slug": "goa",
        "best_time": "Nov",
        "popular_attractions": ["A", "B"],
    }]
    mock_pricing.return_value = {"public_pricing": ["₹1000/day"]}
    output = dcs.list_destinations()
    self.assertEqual(output[0]["name"], "Goa")
    self.assertEqual(output[0]["price_preview"], "₹1000/day")


_add_test("test_list_destinations_basic_mapping")(_test_list_destinations_basic_mapping)


@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": ["P"]})
@patch("app.services.destination_compare_service._parse_destinations")
def _test_list_destinations_top_attractions_preview_limited_to_three(self, mock_parse, _mock_pricing):
    mock_parse.return_value = [{
        "name": "Goa",
        "slug": "goa",
        "best_time": "Nov",
        "popular_attractions": ["A", "B", "C", "D"],
    }]
    output = dcs.list_destinations()
    self.assertEqual(output[0]["top_attractions_preview"], ["A", "B", "C"])


_add_test("test_list_destinations_top_attractions_preview_limited_to_three")(_test_list_destinations_top_attractions_preview_limited_to_three)


@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": []})
@patch("app.services.destination_compare_service._parse_destinations")
def _test_list_destinations_price_preview_empty_if_no_pricing(self, mock_parse, _mock_pricing):
    mock_parse.return_value = [{
        "name": "Goa",
        "slug": "goa",
        "best_time": "Nov",
        "popular_attractions": ["A"],
    }]
    output = dcs.list_destinations()
    self.assertEqual(output[0]["price_preview"], "")


_add_test("test_list_destinations_price_preview_empty_if_no_pricing")(_test_list_destinations_price_preview_empty_if_no_pricing)


@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": ["P"]})
@patch("app.services.destination_compare_service._parse_destinations")
def _test_list_destinations_order_preserved(self, mock_parse, _mock_pricing):
    mock_parse.return_value = [
        {"name": "A", "slug": "a", "best_time": "x", "popular_attractions": []},
        {"name": "B", "slug": "b", "best_time": "y", "popular_attractions": []},
    ]
    output = dcs.list_destinations()
    self.assertEqual([entry["name"] for entry in output], ["A", "B"])


_add_test("test_list_destinations_order_preserved")(_test_list_destinations_order_preserved)


@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": ["P"]})
@patch("app.services.destination_compare_service._parse_destinations")
def _test_list_destinations_handles_unicode_name(self, mock_parse, _mock_pricing):
    mock_parse.return_value = [{"name": "São Paulo", "slug": "sao-paulo", "best_time": "Any", "popular_attractions": []}]
    output = dcs.list_destinations()
    self.assertEqual(output[0]["name"], "São Paulo")


_add_test("test_list_destinations_handles_unicode_name")(_test_list_destinations_handles_unicode_name)


@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": ["P"]})
@patch("app.services.destination_compare_service._parse_destinations")
def _test_list_destinations_extreme_attraction_text_preview(self, mock_parse, _mock_pricing):
    long_text = "A" * 4000
    mock_parse.return_value = [{
        "name": "Goa",
        "slug": "goa",
        "best_time": "Nov",
        "popular_attractions": [long_text, "B", "C", "D"],
    }]
    output = dcs.list_destinations()
    self.assertEqual(output[0]["top_attractions_preview"][0], long_text)


_add_test("test_list_destinations_extreme_attraction_text_preview")(_test_list_destinations_extreme_attraction_text_preview)


@patch("app.services.destination_compare_service._extract_pricing")
@patch("app.services.destination_compare_service._parse_destinations")
def _test_list_destinations_calls_extract_pricing_per_destination(self, mock_parse, mock_pricing):
    mock_parse.return_value = [
        {"name": "Goa", "slug": "goa", "best_time": "Nov", "popular_attractions": []},
        {"name": "Mysore", "slug": "mysore", "best_time": "Oct", "popular_attractions": []},
    ]
    mock_pricing.return_value = {"public_pricing": ["P"]}
    dcs.list_destinations()
    self.assertEqual(mock_pricing.call_count, 2)


_add_test("test_list_destinations_calls_extract_pricing_per_destination")(_test_list_destinations_calls_extract_pricing_per_destination)


# -------------------------
# 16 compare_destinations tests
# -------------------------


def _base_destination(name="Goa", slug="goa"):
    return {
        "name": name,
        "slug": slug,
        "overview": "Overview",
        "best_time": "Nov",
        "popular_attractions": ["A"],
        "suggested_itinerary": [],
        "food_recommendations": [],
    }


@patch("app.services.destination_compare_service._parse_destinations", return_value=[])
def _test_compare_destinations_empty_requested_returns_empty(self, _mock_parse):
    result = dcs.compare_destinations([])
    self.assertEqual(result["found"], [])
    self.assertEqual(result["missing"], [])
    self.assertEqual(result["ai_verdict"], "")


_add_test("test_compare_destinations_empty_requested_returns_empty")(_test_compare_destinations_empty_requested_returns_empty)


@patch("app.services.destination_compare_service._extract_hotel_pricing", return_value={"hotel_options": ["H"]})
@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": ["P"]})
@patch("app.services.destination_compare_service._parse_destinations", return_value=[_base_destination("Goa", "goa")])
def _test_compare_destinations_local_match_by_name_case_insensitive(self, _mock_parse, _mock_price, _mock_hotels):
    result = dcs.compare_destinations(["goA"])
    self.assertEqual(result["found"][0]["name"], "Goa")


_add_test("test_compare_destinations_local_match_by_name_case_insensitive")(_test_compare_destinations_local_match_by_name_case_insensitive)


@patch("app.services.destination_compare_service._extract_hotel_pricing", return_value={"hotel_options": ["H"]})
@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": ["P"]})
@patch("app.services.destination_compare_service._parse_destinations", return_value=[_base_destination("New York", "new-york")])
def _test_compare_destinations_local_match_by_slug(self, _mock_parse, _mock_price, _mock_hotels):
    result = dcs.compare_destinations(["new-york"])
    self.assertEqual(result["found"][0]["name"], "New York")


_add_test("test_compare_destinations_local_match_by_slug")(_test_compare_destinations_local_match_by_slug)


@patch("app.services.destination_compare_service._extract_hotel_pricing", return_value={"hotel_options": ["H"]})
@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": ["P"]})
@patch("app.services.destination_compare_service._parse_destinations", return_value=[_base_destination("Goa", "goa")])
def _test_compare_destinations_requested_whitespace_trimmed(self, _mock_parse, _mock_price, _mock_hotels):
    result = dcs.compare_destinations(["  Goa  "])
    self.assertEqual(result["found"][0]["name"], "Goa")


_add_test("test_compare_destinations_requested_whitespace_trimmed")(_test_compare_destinations_requested_whitespace_trimmed)


@patch("app.services.destination_compare_service.ask_groq_llm", return_value="")
@patch("app.services.destination_compare_service._fetch_hotels_data", return_value="Hotel A\nHotel B")
@patch("app.services.destination_compare_service._fetch_activities_data", return_value="Fort\nMuseum")
@patch("app.services.destination_compare_service._fetch_weather_data", return_value="Sunny")
@patch("app.services.destination_compare_service._extract_hotel_pricing", return_value={"hotel_options": []})
@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": []})
@patch("app.services.destination_compare_service._parse_destinations", return_value=[])
def _test_compare_destinations_missing_fallback_success(self, _mock_parse, _mock_price, _mock_hotels_local, _mock_weather, _mock_activities, _mock_hotels, _mock_llm):
    result = dcs.compare_destinations(["Atlantis"])
    self.assertEqual(result["found"][0]["name"], "Atlantis")
    self.assertEqual(result["found"][0]["popular_attractions"], ["Fort", "Museum"])
    self.assertEqual(result["missing"], [])


_add_test("test_compare_destinations_missing_fallback_success")(_test_compare_destinations_missing_fallback_success)


@patch("app.services.destination_compare_service._fetch_hotels_data", return_value="Hotel A")
@patch("app.services.destination_compare_service._fetch_activities_data", return_value="Error: rate limited")
@patch("app.services.destination_compare_service._fetch_weather_data", return_value="Sunny")
@patch("app.services.destination_compare_service._extract_hotel_pricing", return_value={"hotel_options": []})
@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": []})
@patch("app.services.destination_compare_service._parse_destinations", return_value=[])
def _test_compare_destinations_fallback_activities_error_yields_empty_list(self, _mock_parse, _mock_price, _mock_hotels_local, _mock_weather, _mock_activities, _mock_hotels):
    result = dcs.compare_destinations(["Atlantis"])
    self.assertEqual(result["found"][0]["popular_attractions"], [])


_add_test("test_compare_destinations_fallback_activities_error_yields_empty_list")(_test_compare_destinations_fallback_activities_error_yields_empty_list)


@patch("app.services.destination_compare_service._fetch_hotels_data", return_value="Error: key missing")
@patch("app.services.destination_compare_service._fetch_activities_data", return_value="Fort")
@patch("app.services.destination_compare_service._fetch_weather_data", return_value="Sunny")
@patch("app.services.destination_compare_service._extract_hotel_pricing", return_value={"hotel_options": []})
@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": []})
@patch("app.services.destination_compare_service._parse_destinations", return_value=[])
def _test_compare_destinations_fallback_hotels_error_yields_empty_hotels(self, _mock_parse, _mock_price, _mock_hotels_local, _mock_weather, _mock_activities, _mock_hotels):
    result = dcs.compare_destinations(["Atlantis"])
    self.assertEqual(result["found"][0]["hotel_options"], [])


_add_test("test_compare_destinations_fallback_hotels_error_yields_empty_hotels")(_test_compare_destinations_fallback_hotels_error_yields_empty_hotels)


@patch("app.services.destination_compare_service._fetch_weather_data", side_effect=Exception("network down"))
@patch("app.services.destination_compare_service._extract_hotel_pricing", return_value={"hotel_options": []})
@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": []})
@patch("app.services.destination_compare_service._parse_destinations", return_value=[])
def _test_compare_destinations_fallback_exception_adds_missing(self, _mock_parse, _mock_price, _mock_hotels_local, _mock_weather):
    result = dcs.compare_destinations(["Atlantis"])
    self.assertEqual(result["found"], [])
    self.assertEqual(result["missing"], ["Atlantis"])


_add_test("test_compare_destinations_fallback_exception_adds_missing")(_test_compare_destinations_fallback_exception_adds_missing)


@patch("app.services.destination_compare_service.ask_groq_llm", return_value="Comparison verdict")
@patch("app.services.destination_compare_service._fetch_hotels_data", return_value="Hotel A")
@patch("app.services.destination_compare_service._fetch_activities_data", return_value="Fort")
@patch("app.services.destination_compare_service._fetch_weather_data", return_value="Sunny")
@patch("app.services.destination_compare_service._extract_hotel_pricing", return_value={"hotel_options": []})
@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": []})
@patch("app.services.destination_compare_service._parse_destinations", return_value=[_base_destination("Goa", "goa")])
def _test_compare_destinations_two_found_calls_llm_compare(self, _mock_parse, _mock_price, _mock_hotels_local, _mock_weather, _mock_activities, _mock_hotels, mock_llm):
    result = dcs.compare_destinations(["Goa", "Atlantis"])
    self.assertEqual(result["ai_verdict"], "Comparison verdict")
    self.assertTrue(mock_llm.called)


_add_test("test_compare_destinations_two_found_calls_llm_compare")(_test_compare_destinations_two_found_calls_llm_compare)


@patch("app.services.destination_compare_service.ask_groq_llm", side_effect=Exception("llm boom"))
@patch("app.services.destination_compare_service._fetch_hotels_data", return_value="Hotel A")
@patch("app.services.destination_compare_service._fetch_activities_data", return_value="Fort")
@patch("app.services.destination_compare_service._fetch_weather_data", return_value="Sunny")
@patch("app.services.destination_compare_service._extract_hotel_pricing", return_value={"hotel_options": []})
@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": []})
@patch("app.services.destination_compare_service._parse_destinations", return_value=[_base_destination("Goa", "goa")])
def _test_compare_destinations_two_found_llm_failure_message(self, _mock_parse, _mock_price, _mock_hotels_local, _mock_weather, _mock_activities, _mock_hotels, _mock_llm):
    result = dcs.compare_destinations(["Goa", "Atlantis"])
    self.assertIn("LLM dynamic comparison failed", result["ai_verdict"])


_add_test("test_compare_destinations_two_found_llm_failure_message")(_test_compare_destinations_two_found_llm_failure_message)


@patch("app.services.destination_compare_service.ask_groq_llm", return_value="Summary verdict")
@patch("app.services.destination_compare_service._extract_hotel_pricing", return_value={"hotel_options": ["H"]})
@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": ["P"]})
@patch("app.services.destination_compare_service._parse_destinations", return_value=[_base_destination("Goa", "goa")])
def _test_compare_destinations_single_found_calls_summary_llm(self, _mock_parse, _mock_price, _mock_hotels, mock_llm):
    result = dcs.compare_destinations(["Goa"])
    self.assertEqual(result["ai_verdict"], "Summary verdict")
    self.assertTrue(mock_llm.called)


_add_test("test_compare_destinations_single_found_calls_summary_llm")(_test_compare_destinations_single_found_calls_summary_llm)


@patch("app.services.destination_compare_service.ask_groq_llm", side_effect=Exception("no llm"))
@patch("app.services.destination_compare_service._extract_hotel_pricing", return_value={"hotel_options": ["H"]})
@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": ["P"]})
@patch("app.services.destination_compare_service._parse_destinations", return_value=[_base_destination("Goa", "goa")])
def _test_compare_destinations_single_found_llm_failure_silent(self, _mock_parse, _mock_price, _mock_hotels, _mock_llm):
    result = dcs.compare_destinations(["Goa"])
    self.assertEqual(result["ai_verdict"], "")


_add_test("test_compare_destinations_single_found_llm_failure_silent")(_test_compare_destinations_single_found_llm_failure_silent)


@patch("app.services.destination_compare_service.ask_groq_llm", return_value="")
@patch("app.services.destination_compare_service._extract_hotel_pricing", return_value={"hotel_options": ["H"]})
@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": ["P"]})
@patch("app.services.destination_compare_service._parse_destinations", return_value=[_base_destination("Goa", "goa")])
def _test_compare_destinations_duplicate_requests_duplicate_found(self, _mock_parse, _mock_price, _mock_hotels, _mock_llm):
    result = dcs.compare_destinations(["Goa", "Goa"])
    self.assertEqual(len(result["found"]), 2)


_add_test("test_compare_destinations_duplicate_requests_duplicate_found")(_test_compare_destinations_duplicate_requests_duplicate_found)


@patch("app.services.destination_compare_service.datetime")
@patch("app.services.destination_compare_service._fetch_hotels_data", return_value="Hotel A")
@patch("app.services.destination_compare_service._fetch_activities_data", return_value="Fort")
@patch("app.services.destination_compare_service._fetch_weather_data", return_value="Sunny")
@patch("app.services.destination_compare_service._extract_hotel_pricing", return_value={"hotel_options": []})
@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": []})
@patch("app.services.destination_compare_service._parse_destinations", return_value=[])
def _test_compare_destinations_fallback_uses_dynamic_dates(self, _mock_parse, _mock_price, _mock_hotels_local, _mock_weather, _mock_activities, mock_hotels, mock_datetime):
    mock_datetime.now.return_value = real_datetime(2026, 4, 1)
    dcs.compare_destinations(["Atlantis"])
    args = mock_hotels.call_args.args
    self.assertEqual(args[0], "Atlantis")
    self.assertEqual(args[1], "2026-04-15")
    self.assertEqual(args[2], "2026-04-18")


_add_test("test_compare_destinations_fallback_uses_dynamic_dates")(_test_compare_destinations_fallback_uses_dynamic_dates)


@patch("app.services.destination_compare_service.ask_groq_llm", return_value="")
@patch("app.services.destination_compare_service._extract_hotel_pricing", return_value={"hotel_options": ["H"]})
@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": ["P"]})
@patch("app.services.destination_compare_service._parse_destinations", return_value=[_base_destination("Goa", "goa"), _base_destination("Mysore", "mysore")])
def _test_compare_destinations_total_available_count(self, _mock_parse, _mock_price, _mock_hotels, _mock_llm):
    result = dcs.compare_destinations(["Goa"])
    self.assertEqual(result["total_available"], 2)


_add_test("test_compare_destinations_total_available_count")(_test_compare_destinations_total_available_count)


@patch("app.services.destination_compare_service._fetch_hotels_data", return_value="Hôtel Ω\nRyokan 東京")
@patch("app.services.destination_compare_service._fetch_activities_data", return_value="Café Élan\n古い寺")
@patch("app.services.destination_compare_service._fetch_weather_data", return_value="🌧️")
@patch("app.services.destination_compare_service._extract_hotel_pricing", return_value={"hotel_options": []})
@patch("app.services.destination_compare_service._extract_pricing", return_value={"public_pricing": []})
@patch("app.services.destination_compare_service._parse_destinations", return_value=[])
def _test_compare_destinations_extreme_unicode_text_fallback(self, _mock_parse, _mock_price, _mock_hotels_local, _mock_weather, _mock_activities, _mock_hotels):
    result = dcs.compare_destinations(["  tØkyō — 東京  "])
    self.assertEqual(result["found"][0]["name"], "  Tøkyō — 東京  ")
    self.assertIn("Café Élan", result["found"][0]["popular_attractions"])


_add_test("test_compare_destinations_extreme_unicode_text_fallback")(_test_compare_destinations_extreme_unicode_text_fallback)


if __name__ == "__main__":
    unittest.main()
