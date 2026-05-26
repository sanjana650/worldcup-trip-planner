import argparse
import asyncio
import json
import sys


def print_json(label: str, data):
    print(f"\n=== {label} ===")
    print(json.dumps(data, indent=2, default=str))


def load_tools():
    try:
        from agent.tools import (
            build_trip_itinerary,
            check_visa_requirements,
            estimate_flight_cost,
            generate_trip_data_bundle,
            get_matches_by_team,
        )
    except ModuleNotFoundError as exc:
        print(
            "Could not import project dependencies.\n"
            "Run this from the project root after installing requirements:\n\n"
            "  pip install -r requirements.txt\n",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    return {
        "build_trip_itinerary": build_trip_itinerary,
        "check_visa_requirements": check_visa_requirements,
        "estimate_flight_cost": estimate_flight_cost,
        "generate_trip_data_bundle": generate_trip_data_bundle,
        "get_matches_by_team": get_matches_by_team,
    }


def load_agent_runner():
    try:
        from agent.agent import run_agent
    except ModuleNotFoundError as exc:
        print(
            "Could not import agent dependencies.\n"
            "Run this from the project root after installing requirements:\n\n"
            "  pip install -r requirements.txt\n",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    return run_agent


def run_matches_case(team: str):
    tools = load_tools()
    matches = tools["get_matches_by_team"](team)

    print_json(
        "get_matches_by_team",
        {
            "input": {"team": team},
            "matches_found": len(matches),
            "matches": matches,
        },
    )


def run_visa_case(nationality: str, destination_country: str | None):
    tools = load_tools()
    result = tools["check_visa_requirements"](
        nationality=nationality,
        destination_country=destination_country,
    )

    print_json(
        "check_visa_requirements",
        {
            "input": {
                "nationality": nationality,
                "destination_country": destination_country,
            },
            "result": result,
        },
    )


def run_flight_case(origin_airport: str, itinerary_airports: list[str]):
    tools = load_tools()
    result = tools["estimate_flight_cost"](
        origin_airport=origin_airport,
        itinerary_airports=itinerary_airports,
        include_return=True,
    )

    print_json(
        "estimate_flight_cost",
        {
            "input": {
                "origin_airport": origin_airport,
                "itinerary_airports": itinerary_airports,
            },
            "result": result,
        },
    )


def run_itinerary_case(team: str, nationality: str, origin_airport: str, budget_usd: float | None):
    tools = load_tools()
    result = tools["build_trip_itinerary"](
        team=team,
        nationality=nationality,
        origin_airport=origin_airport,
        budget_usd=budget_usd,
    )

    print_json(
        "build_trip_itinerary",
        {
            "input": {
                "team": team,
                "nationality": nationality,
                "origin_airport": origin_airport,
                "budget_usd": budget_usd,
            },
            "result": result,
        },
    )


def run_bundle_case(team: str, nationality: str, origin_airport: str, budget_usd: float | None):
    tools = load_tools()
    bundle = tools["generate_trip_data_bundle"](
        team=team,
        nationality=nationality,
        origin_airport=origin_airport,
        budget_usd=budget_usd,
    )

    print_json(
        "generate_trip_data_bundle",
        {
            "input": {
                "team": team,
                "nationality": nationality,
                "origin_airport": origin_airport,
                "budget_usd": budget_usd,
            },
            "result": bundle,
        },
    )


def run_all_cases(team: str, nationality: str, origin_airport: str, budget_usd: float | None):
    run_matches_case(team)
    run_visa_case(nationality, None)
    run_flight_case(origin_airport, ["LAX", "DFW", "MEX"])
    run_itinerary_case(team, nationality, origin_airport, budget_usd)
    run_bundle_case(team, nationality, origin_airport, budget_usd)


async def run_agent_case(message: str, session_id: str):
    run_agent = load_agent_runner()
    print(f"\n=== user request ===\n{message}")
    response = await run_agent(message, session_id=session_id)
    print(f"\n=== agent response ===\n{response}")


def main():
    parser = argparse.ArgumentParser(
        description="Run live World Cup trip-planner tool use cases from your laptop."
    )
    parser.add_argument(
        "case",
        choices=["all", "matches", "visa", "flight", "itinerary", "bundle", "agent"],
        help="Use case to run.",
    )
    parser.add_argument(
        "--team",
        default="Korea Republic",
        help="Team name exactly as seeded in MongoDB.",
    )
    parser.add_argument(
        "--nationality",
        default="IND",
        help="Traveler nationality code or label used by the current tools.",
    )
    parser.add_argument(
        "--origin-airport",
        default="DEL",
        help="Traveler origin airport IATA code.",
    )
    parser.add_argument(
        "--budget-usd",
        type=float,
        default=5000,
        help="Traveler budget in USD.",
    )
    parser.add_argument(
        "--destination-country",
        default=None,
        help="Optional country for direct visa checks, like USA, Canada, or Mexico.",
    )
    parser.add_argument(
        "--itinerary-airports",
        nargs="*",
        default=["LAX", "DFW", "MEX"],
        help="Airports for direct flight estimate checks.",
    )
    parser.add_argument(
        "--message",
        default=(
            "I support Korea Republic. I am Indian, flying from DEL, "
            "and my budget is 5000 USD. Plan my World Cup trip."
        ),
        help="Natural-language request to send through the real agent.",
    )
    parser.add_argument(
        "--session-id",
        default="manual-feature-test",
        help="Session id for the agent run.",
    )

    args = parser.parse_args()

    try:
        if args.case == "matches":
            run_matches_case(args.team)
        elif args.case == "visa":
            run_visa_case(args.nationality, args.destination_country)
        elif args.case == "flight":
            run_flight_case(args.origin_airport, args.itinerary_airports)
        elif args.case == "itinerary":
            run_itinerary_case(args.team, args.nationality, args.origin_airport, args.budget_usd)
        elif args.case == "bundle":
            run_bundle_case(args.team, args.nationality, args.origin_airport, args.budget_usd)
        elif args.case == "agent":
            asyncio.run(run_agent_case(args.message, args.session_id))
        else:
            run_all_cases(args.team, args.nationality, args.origin_airport, args.budget_usd)
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    except Exception as exc:
        print(f"Use case failed: {exc}", file=sys.stderr)
        raise SystemExit(3) from exc


if __name__ == "__main__":
    main()
