# backend/app/routes/admin_routes.py
from fastapi import APIRouter, Body, Depends, HTTPException
from app.auth import require_role, get_current_user, create_token
from app.database import read_all
from typing import Dict

router = APIRouter()

@router.post("/login")
def admin_login(data: Dict = Body(...)):
    """
    Convenience admin/login endpoint mapped to /api/admin/login
    Accepts email,password; returns JWT only if user exists and role == superadmin.
    (Useful for the admin panel login path in your UI)
    """
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password required")

    users = read_all("users")
    for u in users:
        if u.get("email") == email and u.get("password") == password:
            if u.get("role") != "superadmin":
                raise HTTPException(status_code=403, detail="Not a superadmin")
            token = create_token({
                "user_id": u.get("id"),
                "role": u.get("role"),
                "company_id": u.get("company_id"),
                "company_name": u.get("company_name"),
                "created_by": u.get("created_by")
            })
            return {"message": "ok", "token": token, "user": {"id": u.get("id"), "email": u.get("email"), "name": u.get("name"), "role": u.get("role")}}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@router.get("/seed")
def seed(user=Depends(require_role(["superadmin"]))):
    return {"message":"ok"}

@router.get("/dump")
def dump_data(user=Depends(require_role(["admin","superadmin"]))):
    return {
        "users": read_all("users"),
        "templates": read_all("templates"),
        "documents": read_all("documents"),
        "companies": read_all("companies")
    }
