from pymongo import MongoClient
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

DATABASE_NAME = "worldcup2026"


def get_mongo_uri() -> str:
    mongo_uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("Missing MongoDB connection string. Set MONGODB_URI or MONGO_URI in your .env file.")

    return mongo_uri


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    return MongoClient(get_mongo_uri())


def get_database():
    return get_mongo_client()[DATABASE_NAME]


def get_collection(collection_name: str):
    return get_database()[collection_name]
