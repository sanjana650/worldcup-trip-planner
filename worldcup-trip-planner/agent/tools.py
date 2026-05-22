# agent/tools.py
from google.adk.tools import FunctionTool
from pymongo import MongoClient
import os

# Create a master function so the LLM doesn't have to cycle back and forth
def generate_trip_data_bundle(team: str, nationality: str, origin_airport: str) -> dict:
    """
    One single call to fetch matches, estimate flights, and grab visa steps.
    """
    # 1. Internal Database lookup right inside the python tool layer
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client["worldcup2026"]
    
    # Grab matches natively
    matches = list(db["matches"].find({"team": team}, {"_id": 0}))
    
    # 2. Native flight estimation calculation
    asia_airports = ["SIN", "KUL", "BKK", "HKG", "NRT"]
    flight_cost = 900 if origin_airport in asia_airports else 280
    
    # 3. Native visa rule dictionary match
    visa_db = {
        "Singaporean": {"USA": "ESTA required ($21)", "Canada": "eTA required ($7)", "Mexico": "No visa required"},
        "British": {"USA": "ESTA required ($21)", "Canada": "eTA required ($7)", "Mexico": "No visa required"}
    }
    visa_rules = visa_db.get(nationality, {"USA": "Check official guidelines"})

    return {
        "matches_found": matches,
        "flight_estimate_usd": flight_cost,
        "visa_requirements": visa_rules
    }

# Register this single consolidated tool for processing
master_travel_tool = FunctionTool(func=generate_trip_data_bundle)



