import unittest
from unittest.mock import patch

try:
    from agent import tools
except ModuleNotFoundError as exc:
    tools = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


class FakeCursor:
    def __init__(self, documents):
        self.documents = documents

    def __iter__(self):
        return iter(self.documents)

    def sort(self, field_name, direction):
        reverse = direction == -1
        return sorted(self.documents, key=lambda item: item.get(field_name, ""), reverse=reverse)


class FakeCollection:
    def __init__(self, documents, collection_name):
        self.documents = documents
        self.collection_name = collection_name
        self.last_query = None
        self.last_projection = None

    def find(self, query, projection):
        self.last_query = query
        self.last_projection = projection

        if self.collection_name == "cities":
            return FakeCursor([self.apply_projection(document.copy(), projection) for document in self.documents])

        requested_team = query.get("teams")
        matches = [
            document.copy()
            for document in self.documents
            if requested_team in document.get("teams", [])
        ]

        return FakeCursor([self.apply_projection(match, projection) for match in matches])

    def find_one(self, query, projection):
        for document in self.documents:
            if document.get("_id") == query.get("_id"):
                return self.apply_projection(document.copy(), projection)

        return None

    def apply_projection(self, document, projection):
        if projection and projection.get("_id") == 0:
            document.pop("_id", None)

        return document


class FakeDatabase:
    def __init__(self, matches, cities=None):
        self.matches_collection = FakeCollection(matches, "matches")
        self.cities_collection = FakeCollection(cities or [], "cities")

    def __getitem__(self, collection_name):
        if collection_name == "matches":
            return self.matches_collection
        if collection_name == "cities":
            return self.cities_collection

        raise KeyError(collection_name)


class ToolUseCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if tools is None:
            raise unittest.SkipTest(f"Project dependencies are not installed: {IMPORT_ERROR}")

    def setUp(self):
        self.fake_matches = [
            {
                "_id": "mongo-id-1",
                "match_no": 2,
                "date": "2026-06-13",
                "teams": ["Korea Republic", "Czechia"],
                "location_city_id": "city-1",
                "stadium": "BMO Field",
            },
            {
                "_id": "mongo-id-2",
                "match_no": 1,
                "date": "2026-06-11",
                "teams": ["Mexico", "Korea Republic"],
                "location_city_id": "city-1",
                "stadium": "Estadio Azteca",
            },
            {
                "_id": "mongo-id-3",
                "match_no": 3,
                "date": "2026-06-15",
                "teams": ["Brazil", "Morocco"],
                "location_city_id": "city-3",
                "stadium": "SoFi Stadium",
            },
        ]
        self.fake_cities = [
            {
                "_id": "city-1",
                "name": "Los Angeles",
                "country": "USA",
                "airports": ["LAX"],
                "avg_hotel_cost_per_night": 450,
                "visa_requirements": {
                    "IND": "B1/B2 Tourist Visa required.",
                    "GBR": "Electronic System for Travel Authorization (ESTA) required.",
                },
            },
            {
                "_id": "city-2",
                "name": "Toronto",
                "country": "Canada",
                "airports": ["YYZ"],
                "avg_hotel_cost_per_night": 310,
                "visa_requirements": {
                    "IND": "Temporary Resident Visa (TRV) required in advance.",
                    "GBR": "Electronic Travel Authorization (eTA) required if flying.",
                },
            },
            {
                "_id": "city-3",
                "name": "Mexico City",
                "country": "Mexico",
                "airports": ["MEX"],
                "avg_hotel_cost_per_night": 220,
                "visa_requirements": {
                    "IND": "Visa required unless holding a valid US/UK/Schengen visa.",
                    "GBR": "No visa required for tourism up to 180 days.",
                },
            },
        ]

        self.fake_db = FakeDatabase(self.fake_matches, self.fake_cities)

    def test_get_matches_by_team_returns_matching_matches_sorted_by_date(self):
        with patch.object(tools, "get_database", return_value=self.fake_db):
            matches = tools.get_matches_by_team("Korea Republic")

        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0]["match_no"], 1)
        self.assertEqual(matches[1]["match_no"], 2)
        self.assertNotIn("_id", matches[0])

    def test_get_matches_by_team_queries_seeded_teams_array(self):
        with patch.object(tools, "get_database", return_value=self.fake_db):
            tools.get_matches_by_team("Brazil")

        self.assertEqual(self.fake_db.matches_collection.last_query, {"teams": "Brazil"})
        self.assertEqual(self.fake_db.matches_collection.last_projection, {"_id": 0})

    def test_get_matches_by_team_returns_empty_list_for_unknown_team(self):
        with patch.object(tools, "get_database", return_value=self.fake_db):
            matches = tools.get_matches_by_team("Atlantis FC")

        self.assertEqual(matches, [])

    def test_get_matches_by_team_returns_empty_list_for_blank_team(self):
        with patch.object(tools, "get_database", return_value=self.fake_db) as mocked_get_database:
            matches = tools.get_matches_by_team("   ")

        self.assertEqual(matches, [])
        mocked_get_database.assert_not_called()

    def test_basic_flight_estimate_treats_del_as_asia(self):
        estimate = tools.estimate_basic_flight_cost("DEL")

        self.assertEqual(estimate["estimated_usd"], 1200)
        self.assertEqual(estimate["confidence"], "medium")

    def test_basic_flight_estimate_treats_mumbai_and_bom_as_asia(self):
        bom_estimate = tools.estimate_basic_flight_cost("BOM")
        mumbai_estimate = tools.estimate_basic_flight_cost("Mumbai")

        self.assertEqual(bom_estimate["estimated_usd"], 1200)
        self.assertEqual(mumbai_estimate["estimated_usd"], 1200)

    def test_estimate_flight_cost_builds_multi_leg_route_with_return(self):
        estimate = tools.estimate_flight_cost(
            origin_airport="DEL",
            itinerary_airports=["LAX", "DFW"],
            include_return=True,
        )

        self.assertEqual(estimate["estimated_usd"], 2680)
        self.assertEqual(len(estimate["legs"]), 3)
        self.assertEqual(estimate["legs"][0]["origin_airport"], "DEL")
        self.assertEqual(estimate["legs"][0]["destination_airport"], "LAX")

    def test_basic_visa_requirements_support_ind_and_indian(self):
        ind_rules = tools.check_basic_visa_requirements("IND")
        indian_rules = tools.check_basic_visa_requirements("Indian")

        self.assertEqual(ind_rules["USA"], "B1/B2 Tourist Visa required.")
        self.assertEqual(indian_rules["Canada"], "Temporary Resident Visa (TRV) required in advance.")
        self.assertIn("valid US/UK/Schengen visa", ind_rules["Mexico"])

    def test_check_visa_requirements_uses_city_collection(self):
        with patch.object(tools, "get_database", return_value=self.fake_db):
            result = tools.check_visa_requirements("IND", "USA")

        self.assertEqual(result["requirements"]["USA"]["source"], "cities_collection")
        self.assertEqual(result["requirements"]["USA"]["status"], "visa_required")

    def test_generate_trip_data_bundle_detects_missing_team(self):
        with patch.object(tools, "get_database", return_value=self.fake_db):
            result = tools.generate_trip_data_bundle("", "IND", "DEL", 5000)

        self.assertEqual(result["status"], "missing_team")
        self.assertIn("Team is missing", result["edge_cases"]["warnings"][0])

    def test_generate_trip_data_bundle_detects_team_not_found(self):
        with patch.object(tools, "get_database", return_value=self.fake_db):
            result = tools.generate_trip_data_bundle("Atlantis FC", "IND", "DEL", 5000)

        self.assertEqual(result["status"], "team_not_found")
        self.assertEqual(result["matches_found"], [])

    def test_generate_trip_data_bundle_detects_low_budget(self):
        with patch.object(tools, "get_database", return_value=self.fake_db):
            result = tools.generate_trip_data_bundle("Korea Republic", "IND", "DEL", 1000)

        self.assertEqual(result["status"], "budget_too_low")
        self.assertFalse(result["edge_cases"]["within_budget"])
        self.assertGreater(result["edge_cases"]["budget_gap_usd"], 0)

    def test_generate_trip_data_bundle_detects_same_city_back_to_back(self):
        with patch.object(tools, "get_database", return_value=self.fake_db):
            result = tools.generate_trip_data_bundle("Korea Republic", "IND", "DEL", 5000)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["edge_cases"]["same_city_back_to_back"]), 1)
        self.assertIn("same city", result["edge_cases"]["same_city_back_to_back"][0]["recommendation"])

    def test_build_trip_itinerary_returns_stops_travel_legs_and_budget_status(self):
        with patch.object(tools, "get_database", return_value=self.fake_db):
            result = tools.build_trip_itinerary("Korea Republic", "IND", "DEL", 5000)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["stops"]), 2)
        self.assertEqual(result["stops"][1]["hotel_nights"], 0)
        self.assertEqual(result["total_lodging_usd"], 900)
        self.assertEqual(result["flight_estimate"]["estimated_usd"], 2400)
        self.assertTrue(result["within_budget"])

    def test_build_trip_itinerary_detects_budget_gap(self):
        with patch.object(tools, "get_database", return_value=self.fake_db):
            result = tools.build_trip_itinerary("Korea Republic", "IND", "DEL", 1000)

        self.assertEqual(result["status"], "budget_too_low")
        self.assertFalse(result["within_budget"])
        self.assertEqual(result["budget_gap_usd"], 2300)

    @unittest.skip("Implement after knockout advancement update logic is added.")
    def test_knockout_advancement_update_use_cases(self):
        pass


if __name__ == "__main__":
    unittest.main()
