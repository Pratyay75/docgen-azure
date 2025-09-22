# backend/app/routes/template_routes.py
from fastapi import APIRouter, Body, HTTPException, Depends
from typing import List
from app.models import Template
from app.database import read_all, find_by_id, upsert, delete_by_id
from app.auth import get_current_user, require_role
import uuid

router = APIRouter()

def _make_id():
    return str(uuid.uuid4())

@router.post("/")
def create_template(t: Template = Body(...), user=Depends(get_current_user)):
    tpl = t.dict()
    tpl["id"] = _make_id()
    tpl["created_by"] = user.get("id")
    upsert("templates", tpl)
    return {"message": "Template created", "template": tpl}

@router.get("/")
def list_templates():
    return read_all("templates")

@router.get("/{template_id}")
def get_template(template_id: str):
    tpl = find_by_id("templates", template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tpl

@router.delete("/{template_id}")
def delete_template(template_id: str, user=Depends(require_role(["admin","superadmin"]))):
    ok = delete_by_id("templates", template_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message":"Deleted"}
