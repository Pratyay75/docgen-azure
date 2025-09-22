# backend/app/routes/company_routes.py
from fastapi import APIRouter, Body, HTTPException, Depends
from app.database import read_all, find_by_id, upsert, delete_by_id, COLLECTIONS
from app.auth import get_current_user, require_role
import uuid

router = APIRouter()

@router.post("/")
def create_or_update_company(payload: dict = Body(...), user=Depends(get_current_user)):
    """
    Create or update a company.
    If 'id' is present in payload, update the company; otherwise create a new one.
    """
    cid = payload.get("id") or str(uuid.uuid4())
    obj = {
        "id": cid,
        "name": payload.get("name"),
        "email": payload.get("email"),
        "address": payload.get("address"),
        "contact_person_name": payload.get("contact_person_name"),
        "contact_person_phone": payload.get("contact_person_phone"),
        "meta": payload.get("meta", {}),
        "created_by": user.get("id"),
    }
    upsert("companies", obj)
    return {"message": "saved", "company": obj}


@router.get("/")
def list_companies():
    return read_all("companies")


@router.get("/{company_id}")
def get_company(company_id: str):
    c = find_by_id("companies", company_id)
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    return c


@router.delete("/{company_id}")
def delete_company(company_id: str, user=Depends(require_role(["admin", "superadmin"]))):
    """
    Delete a company and cascade delete all its users.
    """
    ok = delete_by_id("companies", company_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found")

    # Cascade delete users under this company
    COLLECTIONS["users"].delete_many({"company_id": company_id})

    return {"message": "deleted (company + users)"}
