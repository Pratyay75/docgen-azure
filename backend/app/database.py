import os
import uuid
from typing import Any, List
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "docgen")  # optional override

if not MONGO_URI:
    raise RuntimeError("MONGO_URI not set in environment. Please set it in .env")

# Create client and database
_client = MongoClient(MONGO_URI)
_db = _client.get_database(MONGO_DB)

# List of collection names used by the app
COLLECTIONS = {
    "users": _db.get_collection("users"),
    "documents": _db.get_collection("documents"),
    "templates": _db.get_collection("templates"),
    "companies": _db.get_collection("companies"),
    # New collection for storing per-user configuration
    "user_configs": _db.get_collection("user_configs"),
}

# Ensure index on 'id' for quick lookups and uniqueness enforcement
for name, coll in COLLECTIONS.items():
    try:
        coll.create_index([("id", ASCENDING)], unique=True)
    except Exception:
        # ignore index creation errors in restricted environments
        pass

def _ensure_id(obj: dict) -> str:
    """Ensure object has an 'id' string field and return it."""
    if not obj.get("id"):
        obj["id"] = str(uuid.uuid4())
    return obj["id"]

def read_all(collection: str) -> List[dict]:
    """Return all documents in the named collection as a list of dicts."""
    if collection not in COLLECTIONS:
        raise ValueError(f"Unknown collection: {collection}")
    return list(COLLECTIONS[collection].find({}, {"_id": 0}))

def write_all(collection: str, data: List[dict]):
    """
    Replace the entire collection with the provided list of dicts.
    (Used by some code paths for simple JSON-like behavior.)
    """
    if collection not in COLLECTIONS:
        raise ValueError(f"Unknown collection: {collection}")
    coll = COLLECTIONS[collection]
    coll.delete_many({})
    if not data:
        return
    for item in data:
        _ensure_id(item)
    try:
        coll.insert_many(data)
    except Exception:
        coll.delete_many({})
        for item in data:
            try:
                coll.insert_one(item)
            except DuplicateKeyError:
                coll.replace_one({"id": item["id"]}, item, upsert=True)

def find_by_id(collection: str, _id: str) -> Any:
    """Return the document where doc['id'] == _id or None."""
    if collection not in COLLECTIONS:
        raise ValueError(f"Unknown collection: {collection}")
    return COLLECTIONS[collection].find_one({"id": _id}, {"_id": 0})

def upsert(collection: str, obj: dict) -> dict:
    """
    Insert or update object by 'id'. Ensures obj has 'id' field.
    Returns the object (with id).
    """
    if collection not in COLLECTIONS:
        raise ValueError(f"Unknown collection: {collection}")
    coll = COLLECTIONS[collection]
    _ensure_id(obj)
    coll.replace_one({"id": obj["id"]}, obj, upsert=True)
    return find_by_id(collection, obj["id"])

def delete_by_id(collection: str, _id: str) -> bool:
    """Delete a document by id. Returns True if a document was deleted."""
    if collection not in COLLECTIONS:
        raise ValueError(f"Unknown collection: {collection}")
    res = COLLECTIONS[collection].delete_one({"id": _id})
    return res.deleted_count > 0

# --- Convenience: seed SUPERADMIN user if env vars provided ---
def _seed_superadmin_if_needed():
    """
    If SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD environment variables exist,
    create the superadmin user if not present.
    NOTE: For production, passwords should be hashed (bcrypt). This is plain text for quick dev.
    """
    from os import getenv
    email = getenv("SUPERADMIN_EMAIL")
    password = getenv("SUPERADMIN_PASSWORD")
    if not email or not password:
        return

    users_coll = COLLECTIONS["users"]
    existing = users_coll.find_one({"email": email})
    if existing:
        return

    uid = str(uuid.uuid4())
    user_obj = {
        "id": uid,
        "email": email,
        "password": password,  # WARNING: plain text, for dev only
        "name": "Super Admin",
        "role": "superadmin"
    }
    try:
        users_coll.insert_one(user_obj)
        print(f"[database] Created SUPERADMIN user: {email}")
    except Exception as e:
        print(f"[database] Failed creating superadmin: {e}")

# Run the seeding on import (safe to run multiple times)
try:
    _seed_superadmin_if_needed()
except Exception:
    pass
