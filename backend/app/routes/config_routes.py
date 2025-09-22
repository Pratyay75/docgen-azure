# backend/app/routes/config_routes.py
from fastapi import APIRouter, Depends, HTTPException, Body
from datetime import datetime
from app.auth import get_current_user
from app.database import find_by_id, upsert
from app.models import UserConfig, SectionDefinition, PageDefinition
from app import ai  # ✅ use ai._build_section_prompt & ai._build_page_prompt

router = APIRouter()


def _apply_prompts_generation(cfg: dict) -> dict:
    """
    For each section and page in the configuration:
    - Always regenerate prompt if configuration fields changed.
    - If user manually edited the prompt, save that edit separately.
    - Always update generated_prompt with the latest (AI or manual).
    """
    from copy import deepcopy
    created_by = cfg.get("created_by") or cfg.get("document_type")

    # -----------------
    # Handle Sections
    # -----------------
    sections = cfg.get("sections") or []
    new_sections = []
    for sec in sections:
        if not isinstance(sec, SectionDefinition):
            sec = SectionDefinition(**sec)
        sec_dict = sec.dict()
        sec_dict["created_by"] = created_by

        manually_edited = sec_dict.get("manually_edited", False)
        editable_prompt = sec_dict.get("editable_prompt")

        # ✅ Always regenerate fresh prompt
        regenerated_prompt = ai._build_section_prompt(sec_dict)

        if manually_edited and editable_prompt:
            # User’s edit is respected as "editable_prompt"
            sec_dict["editable_prompt"] = editable_prompt
            sec_dict["generated_prompt"] = regenerated_prompt  # AI’s latest version
            sec_dict["prompt_used"] = editable_prompt          # Always use the user edit
        else:
            # Use regenerated AI prompt
            sec_dict["generated_prompt"] = regenerated_prompt
            sec_dict["editable_prompt"] = regenerated_prompt
            sec_dict["prompt_used"] = regenerated_prompt

        sec_dict["prompt_last_updated_at"] = datetime.utcnow().isoformat()
        new_sections.append(sec_dict)
    cfg["sections"] = new_sections

    # -----------------
    # Handle Pages
    # -----------------
    pages = cfg.get("pages") or []
    new_pages = []
    for pg in pages:
        if not isinstance(pg, PageDefinition):
            pg = PageDefinition(**pg)
        pg_dict = pg.dict()
        pg_dict["created_by"] = created_by

        manually_edited = pg_dict.get("manually_edited", False)
        editable_prompt = pg_dict.get("editable_prompt")

        # ✅ Always regenerate fresh prompt
        regenerated_prompt = ai._build_page_prompt(pg_dict)

        if manually_edited and editable_prompt:
            pg_dict["editable_prompt"] = editable_prompt
            pg_dict["generated_prompt"] = regenerated_prompt
            pg_dict["prompt_used"] = editable_prompt
        else:
            pg_dict["generated_prompt"] = regenerated_prompt
            pg_dict["editable_prompt"] = regenerated_prompt
            pg_dict["prompt_used"] = regenerated_prompt

        pg_dict["prompt_last_updated_at"] = datetime.utcnow().isoformat()
        new_pages.append(pg_dict)
    cfg["pages"] = new_pages

    return cfg



@router.get("/", response_model=UserConfig)
def get_user_config(user=Depends(get_current_user)):
    """
    Get the saved configuration for the current user.
    Returns 404 if not found.
    """
    cfg = find_by_id("user_configs", user.get("id"))
    if not cfg:
        raise HTTPException(404, "No configuration found for this user")
    return cfg


@router.post("/", response_model=UserConfig)
def create_or_update_config(payload: UserConfig = Body(...), user=Depends(get_current_user)):
    """
    Save (create or update) the configuration for the current user.
    - Enforces one config per user (id = user.id).
    - Preserves user-edited prompts if provided.
    - Regenerates prompts when config fields change.
    """
    cfg_obj = payload.dict(exclude_unset=True)
    cfg_obj["id"] = user.get("id")
    cfg_obj["user_id"] = user.get("id")
    cfg_obj["updated_at"] = datetime.utcnow().isoformat()

    cfg_obj = _apply_prompts_generation(cfg_obj)

    saved = upsert("user_configs", cfg_obj)
    return saved


@router.put("/", response_model=UserConfig)
def update_config(payload: UserConfig = Body(...), user=Depends(get_current_user)):
    """
    Update the configuration for the current user.
    - Preserves user-edited prompts (manually_edited=True).
    - Always regenerates prompts when config fields change.
    """
    cfg_obj = payload.dict(exclude_unset=True)
    cfg_obj["id"] = user.get("id")
    cfg_obj["user_id"] = user.get("id")
    cfg_obj["updated_at"] = datetime.utcnow().isoformat()

    cfg_obj = _apply_prompts_generation(cfg_obj)

    saved = upsert("user_configs", cfg_obj)
    return saved
