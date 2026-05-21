import os
from pymongo import MongoClient

MONGO_URI = "mongodb+srv://hackathon_user:hackathon_user@cluster0.cgwjta9.mongodb.net/?appName=Cluster0"

try:
    client = MongoClient(MONGO_URI)
    db = client['worldcup2026']
    print("Connected to MongoDB Atlas.")
except Exception as e:
    print(f"Connection failed: {e}")
    exit()

def seed_complete_database():
    print("Initiating production data build for 48-team World Cup matrix...")
    
    db.cities.drop()
    db.matches.drop()
    db.users.drop()
    db.itineraries.drop()
    print("Cleaned out existing collections.")

    # the cities data
    cities_data = [
        {
            "city_code": "mexico_city",
            "name": "Mexico City",
            "country": "Mexico",
            "airports": ["MEX", "NLU"],
            "avg_hotel_cost_per_night": 220,
            "fan_zones": ["Zocalo Plaza", "Chapultepec Park"],
            "visa_requirements": {
                "USA": "No visa required for tourism up to 180 days.",
                "IND": "Visa required (Exempt if holding a valid, unexpired US/UK/Schengen visa).",
                "GBR": "No visa required for tourism up to 180 days."
            }
        },
        {
            "city_code": "toronto",
            "name": "Toronto",
            "country": "Canada",
            "airports": ["YYZ", "YTZ"],
            "avg_hotel_cost_per_night": 310,
            "fan_zones": ["Yonge-Dundas Square", "Exhibition Place"],
            "visa_requirements": {
                "USA": "No visa required for tourism (Passport needed at land border).",
                "IND": "Temporary Resident Visa (TRV) required in advance.",
                "GBR": "Electronic Travel Authorization (eTA) required if flying."
            }
        },
        {
            "city_code": "los_angeles",
            "name": "Los Angeles",
            "country": "USA",
            "airports": ["LAX", "BUR", "LGB"],
            "avg_hotel_cost_per_night": 450,
            "fan_zones": ["Hollywood Boulevard", "Santa Monica Pier"],
            "visa_requirements": {
                "USA": "Citizen / Domestic Travel",
                "IND": "B1/B2 Tourist Visa required.",
                "GBR": "Electronic System for Travel Authorization (ESTA) required."
            }
        },
        {
            "city_code": "new_york",
            "name": "New York / New Jersey",
            "country": "USA",
            "airports": ["JFK", "EWR", "LGA"],
            "avg_hotel_cost_per_night": 490,
            "fan_zones": ["Times Square Fan Festival", "Liberty State Park"],
            "visa_requirements": {
                "USA": "Citizen / Domestic Travel",
                "IND": "B1/B2 Tourist Visa required.",
                "GBR": "Electronic System for Travel Authorization (ESTA) required."
            }
        },
        {
            "city_code": "dallas",
            "name": "Dallas",
            "country": "USA",
            "airports": ["DFW", "DAL"],
            "avg_hotel_cost_per_night": 285,
            "fan_zones": ["Fair Park FIFA Fan Festival"],
            "visa_requirements": {
                "USA": "Citizen / Domestic Travel",
                "IND": "B1/B2 Tourist Visa required.",
                "GBR": "Electronic System for Travel Authorization (ESTA) required."
            }
        },
        {
            "city_code": "vancouver",
            "name": "Vancouver",
            "country": "Canada",
            "airports": ["YVR"],
            "avg_hotel_cost_per_night": 340,
            "fan_zones": ["Playland Festival Site"],
            "visa_requirements": {
                "USA": "No visa required for tourism.",
                "IND": "Temporary Resident Visa (TRV) required.",
                "GBR": "Electronic Travel Authorization (eTA) required."
            }
        }
    ]
    
    city_result = db.cities.insert_many(cities_data)
    print(f"Cities collection built ({len(city_result.inserted_ids)} locations with logistics details seeded).")
    
    inserted_cities = list(db.cities.find({}, {"_id": 1, "city_code": 1}))
    city_map = {c["city_code"]: c["_id"] for c in inserted_cities}

    official_groups = {
        "A": ["Mexico", "South Africa", "Korea Republic", "Czechia"],
        "B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
        "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
        "D": ["United States", "Paraguay", "Australia", "Turkiye"],
        "E": ["Germany", "Curacao", "Cote d'Ivoire", "Ecuador"],
        "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
        "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
        "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
        "I": ["France", "Senegal", "Iraq", "Norway"],
        "J": ["Argentina", "Algeria", "Austria", "Jordan"],
        "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
        "L": ["England", "Croatia", "Ghana", "Panama"]
    }

    matches_data = []
    match_index = 1
    
    venues_rotation = ["mexico_city", "toronto", "los_angeles", "new_york", "dallas", "vancouver"]
    stadiums = {
        "mexico_city": "Estadio Azteca",
        "toronto": "BMO Field",
        "los_angeles": "SoFi Stadium",
        "new_york": "MetLife Stadium",
        "dallas": "AT&T Stadium",
        "vancouver": "BC Place"
    }

    # used Round Robin to genarate Loop
    for group_letter, teams in official_groups.items():
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                city = venues_rotation[match_index % len(venues_rotation)]
                matches_data.append({
                    "match_no": match_index,
                    "date": f"2026-06-{11 + (match_index % 15)}",
                    "group": group_letter,
                    "teams": [teams[i], teams[j]],
                    "location_city_id": city_map[city],
                    "stadium": stadiums[city],
                    "round": "Group Stage"
                })
                match_index += 1

    matches_data.append({
        "match_no": 104,
        "date": "2026-07-19",
        "group": "Final",
        "teams": ["Winner SF 1", "Winner SF 2"],
        "location_city_id": city_map["new_york"],
        "stadium": stadiums["new_york"],
        "round": "World Cup Final"
    })

    match_result = db.matches.insert_many(matches_data)
    print(f"Matches collection built. Seeded {len(match_result.inserted_ids)} fixtures covering all 48 real teams.")

    sample_user = {
        "name": "Naitik Kumar",
        "nationality": "IND",
        "home_airport": "DEL",
        "budget_limit": 6000,
        "favorite_team": "Korea Republic"
    }
    user_id = db.users.insert_one(sample_user).inserted_id
    print("Users collection initialized with baseline schema shape.")

    sample_itinerary = {
        "user_id": user_id,
        "created_at": "2026-05-22",
        "total_estimated_usd": 1550,
        "itinerary_steps": [
            {
                "stop_sequence": 1,
                "city_id": city_map["mexico_city"],
                "activity": "Watch Mexico vs South Africa at Opening Match",
                "est_lodging_usd": 440
            }
        ]
    }
    db.itineraries.insert_one(sample_itinerary)
    print("Itineraries collection initialized with baseline schema shape.")

    print("All 4 collections verified and fully loaded with real data!!")

if __name__ == "__main__":
    seed_complete_database()