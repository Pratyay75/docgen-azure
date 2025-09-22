# backend/app/routes/user_routes.py
from fastapi import APIRouter, Body, HTTPException, Depends, status
from typing import List, Dict, Optional
import uuid
import random
import string

from app.database import read_all, find_by_id, upsert, delete_by_id
from app.auth import get_current_user, require_role, create_token

router = APIRouter(tags=["users"])


def _rand_password(length: int = 10) -> str:
    chars = string.ascii_letters + string.digits + "!@#$%^&*()"
    return "".join(random.choice(chars) for _ in range(length))


@router.get("/")
def list_users():
    """
    List users (returns stored objects).
    Each user may contain a company_id field referencing companies collection.
    """
    users = read_all("users")
    companies = {c["id"]: c.get("name") for c in read_all("companies")}
    for u in users:
        cid = u.get("company_id")
        if cid:
            u["company_name"] = companies.get(cid)
    return users


@router.post("/register", status_code=status.HTTP_201_CREATED)
def create_user(payload: Dict = Body(...), user=Depends(require_role(["admin", "superadmin"]))):
    """
    Admin-only: Create a user.
    payload expected fields:
      - email (required)
      - password (optional; if omitted a random password will be generated)
      - name (optional)
      - role (optional; default 'user')
      - company_id (required for company users, must exist if provided)
    """
    email = (payload.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    existing = [u for u in read_all("users") if (u.get("email") or "").lower() == email]
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    company_id = payload.get("company_id")
    if company_id:
        comp = find_by_id("companies", company_id)
        if not comp:
            raise HTTPException(status_code=400, detail="Company not found")

    password = payload.get("password") or _rand_password(10)
    uid = str(uuid.uuid4())
    obj = {
        "id": uid,
        "email": email,
        "password": password,  # plain-text (dev only)
        "name": payload.get("name"),
        "role": payload.get("role") or "user",
        "company_id": company_id,
        "created_by": user.get("id"),
    }
    upsert("users", obj)
    return {"message": "created", "user": obj}


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(payload: Dict = Body(...)):
    """
    Public signup endpoint.
    Expects: { email, password (optional), name (optional) }
    Returns created user (without password) and token.
    """
    email = (payload.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    if any((x.get("email") or "").lower() == email for x in read_all("users")):
        raise HTTPException(status_code=400, detail="Email already used")

    password = payload.get("password") or _rand_password(10)
    uid = str(uuid.uuid4())
    user_obj = {
        "id": uid,
        "email": email,
        "password": password,
        "name": payload.get("name", ""),
        "role": "user",
        "company_id": None,
        "created_by": uid,
    }
    upsert("users", user_obj)

    token = create_token(user_obj)
    user_out = {k: v for k, v in user_obj.items() if k != "password"}
    return {"user": user_out, "token": token}


@router.post("/login")
def login(payload: Dict = Body(...)):
    """
    Public login endpoint.
    Expects: { email, password }
    Returns user (without password) and token.
    """
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    users = read_all("users")
    found = next(
        (u for u in users if (u.get("email") or "").lower() == email and u.get("password") == password),
        None,
    )
    if not found:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(found)
    user_out = {k: v for k, v in found.items() if k != "password"}
    return {"user": user_out, "token": token}


@router.get("/{user_id}")
def get_user(user_id: str):
    u = find_by_id("users", user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if u.get("company_id"):
        c = find_by_id("companies", u["company_id"])
        if c:
            u["company_name"] = c.get("name")
    return u


@router.put("/{user_id}")
def update_user(user_id: str, payload: Dict = Body(...), user=Depends(get_current_user)):
    """
    Update user fields. Allowed fields: name, email, password, role, company_id.
    """
    u = find_by_id("users", user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    if "email" in payload:
        new_email = (payload.get("email") or "").strip().lower()
        if not new_email:
            raise HTTPException(status_code=400, detail="Email cannot be empty")
        duplicates = [
            x for x in read_all("users")
            if (x.get("email") or "").lower() == new_email and x.get("id") != user_id
        ]
        if duplicates:
            raise HTTPException(status_code=400, detail="Email already used by another user")
        u["email"] = new_email

    if "name" in payload:
        u["name"] = payload.get("name")

    if "password" in payload:
        u["password"] = payload.get("password")

    if "role" in payload:
        u["role"] = payload.get("role")

    if "company_id" in payload:
        company_id = payload.get("company_id")
        if company_id:
            comp = find_by_id("companies", company_id)
            if not comp:
                raise HTTPException(status_code=400, detail="Company not found")
        u["company_id"] = company_id

    u["updated_by"] = user.get("id")
    upsert("users", u)
    return {"message": "updated", "user": u}


@router.delete("/{user_id}")
def delete_user(user_id: str, user=Depends(require_role(["admin", "superadmin"]))):
    ok = delete_by_id("users", user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "deleted"}
@router.post("/seed-superadmin")
def seed_superadmin():
    """
    TEMPORARY: Seed a default superadmin user if none exists.
    WARNING: Remove this after first use!
    """
    users = read_all("users")
    if any(u.get("role") == "superadmin" for u in users):
        return {"message": "Superadmin already exists"}

    uid = str(uuid.uuid4())
    obj = {
        "id": uid,
        "email": "admin@docgen.com",
        "password": "supersecurepassword123",   # ⚠️ plain text (your system uses plain text now)
        "name": "Super Admin",
        "role": "superadmin",
        "company_id": None,
        "created_by": uid,
    }
    upsert("users", obj)
    return {"message": "Superadmin created", "user": obj}
