# agent/tools.py
from datetime import date, datetime

from agent.mongodb import get_database

try:
    from bson import ObjectId
except ModuleNotFoundError:
    ObjectId = None

try:
    from google.adk.tools import FunctionTool
except ModuleNotFoundError:
    FunctionTool = None


INDIA_AIRPORT_ALIASES = {
    "DEL",
    "BOM",
    "MUMBAI",
    "IND",
    "INDIA",
}

AIRPORT_ALIASES = {
    "MUMBAI": "BOM",
    "BOMBAY": "BOM",
    "DELHI": "DEL",
    "NEW DELHI": "DEL",
    "IND": "DEL",
    "INDIA": "DEL",
}

ASIA_AIRPORTS = {
    "DEL",
    "BOM",
    "BLR",
    "HYD",
    "MAA",
    "CCU",
    "SIN",
    "KUL",
    "BKK",
    "HKG",
    "NRT",
}

NORTH_AMERICA_AIRPORTS = {
    "ATL",
    "BOS",
    "DFW",
    "EWR",
    "JFK",
    "LAX",
    "MEX",
    "MIA",
    "SEA",
    "SFO",
    "YYZ",
    "YVR",
}

EUROPE_AIRPORTS = {
    "LHR",
    "LGW",
    "CDG",
    "FRA",
    "AMS",
    "MAD",
}

NATIONALITY_ALIASES = {
    "IND": "IND",
    "INDIA": "IND",
    "INDIAN": "IND",
    "USA": "USA",
    "US": "USA",
    "AMERICAN": "USA",
    "GBR": "GBR",
    "UK": "GBR",
    "BRITISH": "GBR",
    "SINGAPOREAN": "SGP",
    "SINGAPORE": "SGP",
    "SGP": "SGP",
}


def normalize_code(value: str) -> str:
    return value.strip().upper() if value else ""


def normalize_airport(value: str) -> str:
    normalized_value = normalize_code(value)
    return AIRPORT_ALIASES.get(normalized_value, normalized_value)


def normalize_nationality(nationality: str) -> str:
    return NATIONALITY_ALIASES.get(normalize_code(nationality), normalize_code(nationality))


def get_airport_region(airport: str) -> str:
    normalized_airport = normalize_airport(airport)
    if normalized_airport in ASIA_AIRPORTS:
        return "asia"
    if normalized_airport in NORTH_AMERICA_AIRPORTS:
        return "north_america"
    if normalized_airport in EUROPE_AIRPORTS:
        return "europe"
    if normalized_airport:
        return "unknown"
    return "missing"


def serialize_mongo_document(document: dict) -> dict:
    clean_document = document.copy()
    for key, value in clean_document.items():
        if ObjectId and isinstance(value, ObjectId):
            clean_document[key] = str(value)
    return clean_document


def parse_match_date(match: dict):
    match_date = match.get("date")
    if not match_date:
        return None

    try:
        return datetime.strptime(match_date, "%Y-%m-%d").date()
    except ValueError:
        return None


def get_matches_by_team(team: str) -> list[dict]:
    """
    Fetch matches where the requested team appears in the seeded `teams` array.
    """
    normalized_team = team.strip()
    if not normalized_team:
        return []

    db = get_database()

    matches = list(
        db["matches"].find(
            {"teams": normalized_team},
            {"_id": 0}
        ).sort("date", 1)
    )

    return [serialize_mongo_document(match) for match in matches]


def get_city_by_id(city_id) -> dict | None:
    if not city_id:
        return None

    db = get_database()
    lookup_id = city_id
    if ObjectId and isinstance(city_id, str):
        try:
            lookup_id = ObjectId(city_id)
        except Exception:
            lookup_id = city_id

    city = db["cities"].find_one({"_id": lookup_id}, {"_id": 0})
    return city


def enrich_matches_with_city_data(matches: list[dict]) -> list[dict]:
    enriched_matches = []
    for match in matches:
        enriched_match = match.copy()
        city = get_city_by_id(match.get("location_city_id"))
        if city:
            enriched_match["city"] = {
                "name": city.get("name"),
                "country": city.get("country"),
                "airports": city.get("airports", []),
                "avg_hotel_cost_per_night": city.get("avg_hotel_cost_per_night"),
                "fan_zones": city.get("fan_zones", []),
            }
        else:
            enriched_match["city"] = None

        enriched_matches.append(enriched_match)

    return enriched_matches


def estimate_basic_flight_cost(origin_airport: str) -> dict:
    """
    Temporary region-based flight estimate until the full flight tool is built.
    """
    origin = normalize_airport(origin_airport)

    if origin in INDIA_AIRPORT_ALIASES or origin in ASIA_AIRPORTS:
        return {
            "estimated_usd": 1200,
            "confidence": "medium",
            "notes": ["Asia-to-North-America estimate used."],
        }

    if origin:
        return {
            "estimated_usd": 280,
            "confidence": "low",
            "notes": ["Fallback North America/domestic-style estimate used."],
        }

    return {
        "estimated_usd": 280,
        "confidence": "low",
        "notes": ["Origin airport missing; fallback estimate used."],
    }


def estimate_flight_leg_cost(origin_airport: str, destination_airport: str) -> dict:
    """
    Deterministic route-style estimate for one travel leg.
    """
    origin = normalize_airport(origin_airport)
    destination = normalize_airport(destination_airport)
    origin_region = get_airport_region(origin)
    destination_region = get_airport_region(destination)
    notes = []

    if not origin or not destination:
        return {
            "origin_airport": origin or origin_airport,
            "destination_airport": destination or destination_airport,
            "estimated_usd": 0,
            "confidence": "low",
            "notes": ["Missing origin or destination airport; leg cost not estimated."],
        }

    if origin == destination:
        return {
            "origin_airport": origin,
            "destination_airport": destination,
            "estimated_usd": 0,
            "confidence": "high",
            "notes": ["Same airport; no flight needed."],
        }

    route_regions = {origin_region, destination_region}
    if "unknown" in route_regions:
        notes.append("Unknown airport region; fallback route estimate used.")
        estimated_usd = 500
        confidence = "low"
    elif origin_region == destination_region == "north_america":
        estimated_usd = 280
        confidence = "medium"
    elif origin_region == destination_region == "asia":
        estimated_usd = 260
        confidence = "medium"
    elif route_regions == {"asia", "north_america"}:
        estimated_usd = 1200
        confidence = "medium"
    elif route_regions == {"europe", "north_america"}:
        estimated_usd = 800
        confidence = "medium"
    elif route_regions == {"asia", "europe"}:
        estimated_usd = 650
        confidence = "medium"
    else:
        estimated_usd = 500
        confidence = "low"

    return {
        "origin_airport": origin,
        "destination_airport": destination,
        "estimated_usd": estimated_usd,
        "confidence": confidence,
        "notes": notes,
    }


def get_match_primary_airport(match: dict) -> str | None:
    city = match.get("city") or {}
    airports = city.get("airports") or []
    return airports[0] if airports else None


def estimate_flight_cost(
    origin_airport: str,
    destination_airport: str | None = None,
    itinerary_airports: list[str] | None = None,
    include_return: bool = True,
) -> dict:
    """
    Estimate travel cost for one destination or a multi-city itinerary.
    """
    origin = normalize_airport(origin_airport)
    destination_airports = itinerary_airports or ([destination_airport] if destination_airport else [])
    normalized_destinations = [normalize_airport(airport) for airport in destination_airports if airport]
    legs = []
    warnings = []

    if not origin:
        warnings.append("Origin airport missing; flight estimate is incomplete.")

    current_airport = origin
    for next_airport in normalized_destinations:
        if not current_airport:
            break
        leg = estimate_flight_leg_cost(current_airport, next_airport)
        legs.append(leg)
        current_airport = next_airport

    if include_return and current_airport and origin and current_airport != origin:
        legs.append(estimate_flight_leg_cost(current_airport, origin))

    if not normalized_destinations:
        basic_estimate = estimate_basic_flight_cost(origin_airport)
        warnings.append("No destination airport provided; basic origin-region estimate used.")
        return {
            "origin_airport": origin or origin_airport,
            "destination_airports": [],
            "estimated_usd": basic_estimate["estimated_usd"],
            "legs": [],
            "confidence": basic_estimate["confidence"],
            "warnings": warnings + basic_estimate.get("notes", []),
        }

    estimated_total = sum(leg["estimated_usd"] for leg in legs)
    leg_confidences = {leg["confidence"] for leg in legs}
    confidence = "low" if "low" in leg_confidences else "medium"
    if leg_confidences == {"high"}:
        confidence = "high"

    return {
        "origin_airport": origin,
        "destination_airports": normalized_destinations,
        "estimated_usd": estimated_total,
        "legs": legs,
        "confidence": confidence,
        "warnings": warnings,
    }


def check_basic_visa_requirements(nationality: str) -> dict:
    """
    Temporary nationality lookup until the full visa tool is built.
    """
    nationality_code = normalize_nationality(nationality)
    visa_db = {
        "IND": {
            "USA": "B1/B2 Tourist Visa required.",
            "Canada": "Temporary Resident Visa (TRV) required in advance.",
            "Mexico": "Visa required unless holding a valid US/UK/Schengen visa.",
        },
        "SGP": {
            "USA": "ESTA required ($21).",
            "Canada": "eTA required ($7).",
            "Mexico": "No visa required.",
        },
        "GBR": {
            "USA": "ESTA required.",
            "Canada": "eTA required if flying.",
            "Mexico": "No visa required.",
        },
        "USA": {
            "USA": "Citizen / Domestic Travel.",
            "Canada": "No visa required for tourism.",
            "Mexico": "No visa required for tourism up to 180 days.",
        },
    }

    return visa_db.get(
        nationality_code,
        {
            "USA": "Check official guidelines.",
            "Canada": "Check official guidelines.",
            "Mexico": "Check official guidelines.",
        },
    )


def classify_visa_status(requirement: str) -> str:
    normalized_requirement = normalize_code(requirement)
    if "NO VISA" in normalized_requirement or "CITIZEN" in normalized_requirement:
        return "no_visa_required"
    if "ESTA" in normalized_requirement or "ETA" in normalized_requirement:
        return "electronic_authorization_required"
    if "VISA REQUIRED" in normalized_requirement or "TRV" in normalized_requirement or "B1/B2" in normalized_requirement:
        return "visa_required"
    return "check_official_guidelines"


def check_visa_requirements(nationality: str, destination_country: str | None = None) -> dict:
    """
    Return visa requirements for one destination country, or all seeded host countries.
    Prefers city data in MongoDB and falls back to the temporary nationality table.
    """
    nationality_code = normalize_nationality(nationality)
    requested_country = normalize_code(destination_country)
    db = get_database()

    country_rules = {}
    cities = list(db["cities"].find({}, {"_id": 0, "country": 1, "visa_requirements": 1}))
    for city in cities:
        country = city.get("country")
        if not country:
            continue

        if requested_country and normalize_code(country) != requested_country:
            continue

        requirement = city.get("visa_requirements", {}).get(nationality_code)
        if requirement:
            country_rules[country] = {
                "requirement": requirement,
                "status": classify_visa_status(requirement),
                "source": "cities_collection",
            }

    if country_rules:
        return {
            "nationality": nationality_code or nationality,
            "destination_country": destination_country or "all_seeded_host_countries",
            "requirements": country_rules,
            "warnings": [],
        }

    fallback_rules = check_basic_visa_requirements(nationality)
    if requested_country:
        matched_country = next(
            (country for country in fallback_rules if normalize_code(country) == requested_country),
            None,
        )
        if matched_country:
            fallback_rules = {matched_country: fallback_rules[matched_country]}

    warnings = []
    if not nationality_code:
        warnings.append("Nationality is missing; visa requirements need official confirmation.")
    if requested_country and not fallback_rules:
        warnings.append(f"No visa data found for {destination_country}.")

    return {
        "nationality": nationality_code or nationality,
        "destination_country": destination_country or "all_seeded_host_countries",
        "requirements": {
            country: {
                "requirement": requirement,
                "status": classify_visa_status(requirement),
                "source": "fallback_table",
            }
            for country, requirement in fallback_rules.items()
        },
        "warnings": warnings,
    }


def get_upcoming_matches(matches: list[dict], today: date | None = None) -> list[dict]:
    today = today or date.today()
    upcoming_matches = []
    for match in matches:
        match_date = parse_match_date(match)
        if not match_date or match_date >= today:
            upcoming_matches.append(match)

    return upcoming_matches


def find_same_city_back_to_back_matches(matches: list[dict]) -> list[dict]:
    sorted_matches = sorted(matches, key=lambda match: match.get("date", ""))
    same_city_groups = []

    for previous_match, current_match in zip(sorted_matches, sorted_matches[1:]):
        previous_city_id = previous_match.get("location_city_id")
        current_city_id = current_match.get("location_city_id")
        previous_date = parse_match_date(previous_match)
        current_date = parse_match_date(current_match)

        if not previous_city_id or previous_city_id != current_city_id:
            continue
        if not previous_date or not current_date:
            continue

        days_apart = (current_date - previous_date).days
        if 0 <= days_apart <= 3:
            same_city_groups.append({
                "city_id": previous_city_id,
                "match_numbers": [previous_match.get("match_no"), current_match.get("match_no")],
                "dates": [previous_match.get("date"), current_match.get("date")],
                "days_apart": days_apart,
                "recommendation": "Stay in the same city and avoid an extra intercity travel leg.",
            })

    return same_city_groups


def estimate_lodging_total(matches: list[dict]) -> int:
    return sum(stop["lodging_estimate_usd"] for stop in build_itinerary_stops(matches))


def build_itinerary_stops(matches: list[dict]) -> list[dict]:
    stops = []
    previous_city_id = None

    for match in sorted(matches, key=lambda item: item.get("date", "")):
        city = match.get("city") or {}
        nightly_cost = city.get("avg_hotel_cost_per_night") or 250
        city_id = match.get("location_city_id")
        same_city_as_previous = bool(previous_city_id and city_id == previous_city_id)
        hotel_nights = 2 if not same_city_as_previous else 0

        stops.append({
            "match_no": match.get("match_no"),
            "match": " vs ".join(match.get("teams", [])),
            "date": match.get("date"),
            "round": match.get("round"),
            "city": city.get("name"),
            "country": city.get("country"),
            "stadium": match.get("stadium"),
            "airport": get_match_primary_airport(match),
            "hotel_nights": hotel_nights,
            "lodging_estimate_usd": int(nightly_cost * hotel_nights),
            "same_city_as_previous_stop": same_city_as_previous,
        })
        previous_city_id = city_id

    return stops


def build_edge_case_summary(
    team: str,
    matches: list[dict],
    upcoming_matches: list[dict],
    budget_usd: float | None,
    flight_estimate: dict,
) -> dict:
    warnings = []
    status = "ok"
    same_city_back_to_back = find_same_city_back_to_back_matches(upcoming_matches)

    if not team or not team.strip():
        status = "missing_team"
        warnings.append("Team is missing. Ask the user which team they support.")
    elif not matches:
        status = "team_not_found"
        warnings.append("No seeded fixtures were found for this team.")
    elif not upcoming_matches:
        status = "team_eliminated_or_no_future_matches"
        warnings.append("No future fixtures were found; the team may be eliminated or knockout data may be missing.")

    if same_city_back_to_back:
        warnings.append("Same-city back-to-back matches found; keep the traveler in that city.")

    lodging_total = estimate_lodging_total(upcoming_matches)
    estimated_minimum_total = int((flight_estimate.get("estimated_usd") or 0) + lodging_total)
    budget_gap = 0

    if budget_usd is not None and estimated_minimum_total > budget_usd:
        status = "budget_too_low" if status == "ok" else status
        budget_gap = int(estimated_minimum_total - budget_usd)
        warnings.append(f"Budget is too low by about ${budget_gap}.")

    return {
        "status": status,
        "warnings": warnings,
        "same_city_back_to_back": same_city_back_to_back,
        "estimated_minimum_total_usd": estimated_minimum_total,
        "lodging_estimate_usd": lodging_total,
        "budget_usd": budget_usd,
        "budget_gap_usd": budget_gap,
        "within_budget": budget_usd is None or estimated_minimum_total <= budget_usd,
    }


def build_trip_itinerary(
    team: str,
    nationality: str,
    origin_airport: str,
    budget_usd: float | None = None,
) -> dict:
    """
    Build a structured itinerary using seeded match/city data and deterministic estimates.
    """
    matches = get_matches_by_team(team)
    enriched_matches = enrich_matches_with_city_data(matches)
    upcoming_matches = get_upcoming_matches(enriched_matches)
    stops = build_itinerary_stops(upcoming_matches)
    itinerary_airports = [
        stop["airport"]
        for stop in stops
        if stop.get("airport") and not stop.get("same_city_as_previous_stop")
    ]
    flight_estimate = estimate_flight_cost(
        origin_airport=origin_airport,
        itinerary_airports=itinerary_airports,
        include_return=True,
    )
    visa_rules = check_visa_requirements(nationality)
    edge_cases = build_edge_case_summary(
        team=team,
        matches=enriched_matches,
        upcoming_matches=upcoming_matches,
        budget_usd=budget_usd,
        flight_estimate=flight_estimate,
    )

    total_lodging_usd = sum(stop["lodging_estimate_usd"] for stop in stops)
    total_estimated_usd = int(flight_estimate["estimated_usd"] + total_lodging_usd)
    budget_gap_usd = 0
    if budget_usd is not None and total_estimated_usd > budget_usd:
        budget_gap_usd = int(total_estimated_usd - budget_usd)

    return {
        "status": "budget_too_low" if budget_gap_usd and edge_cases["status"] == "ok" else edge_cases["status"],
        "team": team,
        "nationality": normalize_nationality(nationality),
        "origin_airport": normalize_airport(origin_airport),
        "budget_usd": budget_usd,
        "stops": stops,
        "travel_legs": flight_estimate["legs"],
        "flight_estimate": flight_estimate,
        "total_lodging_usd": total_lodging_usd,
        "total_estimated_usd": total_estimated_usd,
        "within_budget": budget_usd is None or total_estimated_usd <= budget_usd,
        "budget_gap_usd": budget_gap_usd,
        "visa_requirements": visa_rules,
        "edge_cases": edge_cases,
        "warnings": edge_cases["warnings"] + flight_estimate.get("warnings", []) + visa_rules.get("warnings", []),
    }

# Create a master function so the LLM doesn't have to cycle back and forth
def generate_trip_data_bundle(
    team: str,
    nationality: str,
    origin_airport: str,
    budget_usd: float | None = None,
) -> dict:
    """
    One single call to fetch matches, estimate flights, and grab visa steps.
    """
    # Grab matches natively
    matches = get_matches_by_team(team)
    enriched_matches = enrich_matches_with_city_data(matches)
    upcoming_matches = get_upcoming_matches(enriched_matches)
    
    # 2. Native flight estimation calculation
    itinerary_airports = [
        get_match_primary_airport(match)
        for match in upcoming_matches
        if get_match_primary_airport(match)
    ]
    flight_estimate = estimate_flight_cost(
        origin_airport=origin_airport,
        itinerary_airports=itinerary_airports,
        include_return=True,
    )
    
    # 3. Native visa lookup
    visa_rules = check_visa_requirements(nationality)
    edge_cases = build_edge_case_summary(
        team=team,
        matches=enriched_matches,
        upcoming_matches=upcoming_matches,
        budget_usd=budget_usd,
        flight_estimate=flight_estimate,
    )

    return {
        "status": edge_cases["status"],
        "matches_found": enriched_matches,
        "upcoming_matches": upcoming_matches,
        "flight_estimate_usd": flight_estimate["estimated_usd"],
        "flight_estimate": flight_estimate,
        "visa_requirements": visa_rules,
        "edge_cases": edge_cases,
        "itinerary": build_trip_itinerary(team, nationality, origin_airport, budget_usd),
    }

# Register this single consolidated tool for processing
master_travel_tool = FunctionTool(func=generate_trip_data_bundle) if FunctionTool else None
visa_requirements_tool = FunctionTool(func=check_visa_requirements) if FunctionTool else None
flight_estimate_tool = FunctionTool(func=estimate_flight_cost) if FunctionTool else None
itinerary_tool = FunctionTool(func=build_trip_itinerary) if FunctionTool else None
