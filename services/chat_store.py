"""
MongoDB-backed chat message store.
Stores and retrieves chat history per user.
"""
from pymongo import MongoClient
from datetime import datetime
import os

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "hms_3")

client = MongoClient(MONGO_URL)
db = client[MONGO_DB]
chat_collection = db["chat_messages"]

# Index for fast lookups by user email
chat_collection.create_index("email")


def save_message(email: str, role: str, text: str):
    """Save a chat message to MongoDB."""
    chat_collection.insert_one({
        "email": email,
        "role": role,
        "text": text,
        "timestamp": datetime.utcnow()
    })


def get_history(email: str, limit: int = 50) -> list:
    """Get recent chat history for a user."""
    messages = chat_collection.find(
        {"email": email},
        {"_id": 0, "role": 1, "text": 1, "timestamp": 1}
    ).sort("timestamp", 1).limit(limit)
    return list(messages)


def clear_history(email: str):
    """Clear chat history for a user."""
    chat_collection.delete_many({"email": email})
