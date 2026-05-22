from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))

db = client["worldcup2026"]

matches_collection = db["matches"]
cities_collection = db["cities"]