# backend/app/routes/document_routes.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body, Query, Request
import os
import uuid
import json
import logging
import io
import datetime
import re
import html as pyhtml
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from docx import Document  # still needed for htmldocx
from htmldocx import HtmlToDocx


from app.models import (
    CreateDocumentRequest,
    RegenerateSectionRequest,
    RegeneratePageRequest,
    RegenerateDocumentRequest,
    PageDefinition,
)
from app.database import upsert, find_by_id
from app.auth import get_current_user
from app import ai, ocr

from fastapi.responses import StreamingResponse, JSONResponse

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


router = APIRouter()
BASE_DIR = os.path.dirname(__file__)
STORAGE_DIR = os.path.join(os.path.dirname(BASE_DIR), "uploads")
os.makedirs(STORAGE_DIR, exist_ok=True)


def _make_id() -> str:
    return str(uuid.uuid4())


def _can_access_doc(user: dict, doc: dict) -> bool:
    if user.get("role") == "superadmin":
        return True
    if user.get("role") == "admin":
        comp = user.get("company_id")
        return (comp and doc.get("company_id") == comp) or doc.get("user_id") == user.get("id")
    return doc.get("user_id") == user.get("id")


# --- User Config helpers ---
def _get_user_config(user: dict) -> Optional[dict]:
    try:
        if not user or not user.get("id"):
            return None
        return find_by_id("user_configs", user.get("id"))
    except Exception:
        logger.exception("Failed to load user config for user id=%s", user.get("id") if user else None)
        return None


def _ensure_user_config_or_403(user: dict):
    if user.get("role") == "superadmin":
        return
    cfg = _get_user_config(user)
    has_pages = bool(cfg and isinstance(cfg.get("pages"), list) and len(cfg["pages"]) > 0)
    has_sections = bool(cfg and isinstance(cfg.get("sections"), list) and len(cfg["sections"]) > 0)
    if not (has_pages or has_sections):
        raise HTTPException(status_code=403, detail="Please configure pages/sections first before uploading or generating.")


# -----------------
# Upload endpoint
# -----------------
@router.post("/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    _ensure_user_config_or_403(user)

    ext = os.path.splitext(file.filename)[1].lower()
    tmp_name = _make_id() + ext
    path = os.path.join(STORAGE_DIR, tmp_name)

    try:
        with open(path, "wb") as f:
            f.write(await file.read())
    except Exception:
        logger.exception("Failed to save uploaded file to path=%s", path)
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    text = ""
    try:
        text = ocr.extract_text_with_azure(path) or ""
    except Exception as e:
        logger.exception("OCR extraction failed for path=%s: %s", path, e)
        text = ""

    # ✅ Always define now here (outside try/except)
    now = datetime.datetime.utcnow().isoformat()
    doc_id = _make_id()

    db_doc = {
        "id": doc_id,
        "filename": file.filename,
        "path": path,
        "raw_text": text,
        "created_at": now,
        "updated_at": now,
        "user_id": user.get("id"),
        "company_id": user.get("company_id"),
        "company_name": user.get("company_name"),
    }

    upsert("documents", db_doc)

    return {
        "id": doc_id,
        "filename": file.filename,
        "path": path,
        "raw_text": text,
        "extracted_text": text,
    }




def _try_load_raw_text_from_path(path: Optional[str]) -> str:
    if not path:
        return ""
    try:
        if os.path.exists(path):
            return ocr.extract_text_with_azure(path) or ""
    except Exception as e:
        logger.exception("Failed to load raw_text from path '%s': %s", path, e)
    return ""


# -----------------
# Generate endpoint
# -----------------
@router.post("/generate")
def generate_document(payload: CreateDocumentRequest = Body(...), user=Depends(get_current_user)):
    raw_text = (payload.raw_text or "").strip()
    file_path = getattr(payload, "file_path", None) or getattr(payload, "path", None)
    if not raw_text and file_path:
        raw_text = _try_load_raw_text_from_path(file_path)

    user_config = _get_user_config(user)
    provided_pages = [p.dict() for p in payload.pages] if getattr(payload, "pages", None) else None
    provided_sections = [s.dict() for s in payload.sections] if getattr(payload, "sections", None) else None

    pages_override = provided_pages or (user_config.get("pages") if user_config else []) or []
    sections_override = provided_sections or (user_config.get("sections") if user_config else []) or []

    if not pages_override and not sections_override and user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Please configure pages/sections first before generating.")

# get document_type from user config (if available)
    author_role = user_config.get("created_by") or user_config.get("document_type") if user_config else None

    for p in pages_override:
        try:
            if p.get("manually_edited") and p.get("editable_prompt"):
            # Keep user-edited prompt
                p["generated_prompt"] = p["editable_prompt"]
            else:
            # Fresh auto-generated prompt
                p_with_role = {**p, "created_by": author_role}
                p["generated_prompt"] = ai._build_page_prompt(p_with_role)
                p["manually_edited"] = False
            p["editable_prompt"] = p.get("editable_prompt") or p["generated_prompt"]
            p["prompt_last_updated_at"] = datetime.datetime.utcnow().isoformat()
        except Exception:
            logger.exception("Failed to build page prompt")
            p["generated_prompt"] = p.get("instruction") or ""



    for s in sections_override:
        try:
            if s.get("manually_edited") and s.get("editable_prompt"):
                s["generated_prompt"] = s["editable_prompt"]
            else:
                s["generated_prompt"] = ai._build_section_prompt(s)
                s["manually_edited"] = False
            s["editable_prompt"] = s.get("editable_prompt") or s["generated_prompt"]
            s["prompt_last_updated_at"] = datetime.datetime.utcnow().isoformat()
        except Exception:
            logger.exception("Failed to build section prompt")
            s["generated_prompt"] = s.get("instruction") or ""

    

    ai_resp_str = ""
    try:
        ai_resp_str = ai.generate_document_from_template({}, raw_text, pages_override, sections_override)
    except Exception:
        logger.exception("AI generate_document_from_template call failed.")
        ai_resp_str = ""

    try:
        doc_json = json.loads(ai_resp_str) if ai_resp_str else {"title": "Untitled", "pages": [], "sections": []}
    except Exception:
        logger.exception("[documents] AI returned invalid JSON; fallback")
        doc_json = {"title": "Untitled", "pages": [], "sections": []}

    doc_id = _make_id()
    now = datetime.datetime.utcnow().isoformat()
    db_doc = {
        "id": doc_id,
        "title": doc_json.get("title", "Untitled Document"),
        "raw_text": raw_text,
        "pages": doc_json.get("pages", []),
        "sections": doc_json.get("sections", []),
        "created_at": now,
        "updated_at": now,
        "version": 1,
        "user_id": user.get("id"),
        "company_id": user.get("company_id"),
        "company_name": user.get("company_name"),
    }
    upsert("documents", db_doc)
    return {"message": "Document generated", "id": doc_id, "document": db_doc}

from app.database import COLLECTIONS

@router.get("/my-documents")
def list_user_documents(user=Depends(get_current_user)):
    """
    Return user's documents sorted by created_at (newest first).
    Cosmos DB Mongo API doesn't allow sort on unindexed fields,
    so we fetch first and then sort in Python.
    """
    docs = list(
        COLLECTIONS["documents"].find(
            {"user_id": user.get("id")},
            {"_id": 0}
        )
    )

    # ✅ Sort in Python (newest first)
    docs.sort(
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )

    return {"documents": docs}





from app.database import delete_by_id

@router.delete("/{doc_id}")
def delete_document(doc_id: str, user=Depends(get_current_user)):
    """
    Delete a document by ID (only if user owns it or has permission).
    """
    doc = find_by_id("documents", doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not _can_access_doc(user, doc):
        raise HTTPException(status_code=403, detail="Access denied")

    ok = delete_by_id("documents", doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Delete failed")

    return {"message": "Document deleted", "id": doc_id}



@router.get("/{doc_id}")
def get_document(doc_id: str, user=Depends(get_current_user)):
    doc = find_by_id("documents", doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not _can_access_doc(user, doc):
        raise HTTPException(status_code=403, detail="Access denied")
    return doc

# -----------------
# Regenerate Section
# -----------------
@router.post("/{doc_id}/regenerate-section")
async def regenerate_section(doc_id: str, payload: RegenerateSectionRequest = Body(...), user=Depends(get_current_user)):
    doc = find_by_id("documents", doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not _can_access_doc(user, doc):
        raise HTTPException(status_code=403, detail="Access denied")

    section = next((s for s in doc.get("sections", []) if s.get("name") == payload.section_name), None)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    raw_text = (payload.raw_text or doc.get("raw_text", "") or "").strip()

    try:
        prompt_to_use = section.get("editable_prompt") or section.get("generated_prompt") or ai._build_section_prompt(section)
        ai_resp = ai.regenerate_section(
            raw_text,
            section.get("content"),
            payload.user_instruction,
            prompt_to_use
        )
    except Exception:
        logger.exception("AI regenerate_section call failed")
        ai_resp = ""

    # ✅ Safe parsing
    new_section = {}
    try:
        parsed = json.loads(ai_resp) if ai_resp else {}
        if isinstance(parsed, dict) and "sections" in parsed:
            new_section = (parsed.get("sections") or [{}])[0]
        elif isinstance(parsed, dict):
            new_section = parsed
        elif isinstance(parsed, str):
            try:
                new_section = json.loads(parsed)
                if not isinstance(new_section, dict):
                    new_section = {"content": parsed, "prompt_used": prompt_to_use}
            except Exception:
                new_section = {"content": parsed, "prompt_used": prompt_to_use}
        else:
            new_section = {"content": str(parsed), "prompt_used": prompt_to_use}
    except Exception:
        logger.exception("Failed to parse AI response while regenerating section.")
        new_section = {"content": "AI error", "prompt_used": prompt_to_use}

    # ✅ Final guarantee: force dict with content
    if not isinstance(new_section, dict):
        new_section = {"content": str(new_section), "prompt_used": prompt_to_use}

    for i, s in enumerate(doc.get("sections", [])):
        if s.get("name") == section.get("name"):
            doc["sections"][i].update({
                "content": new_section.get("content"),
                "prompt_used": new_section.get("prompt_used", prompt_to_use),
                "generated_prompt": section.get("generated_prompt"),
                "editable_prompt": section.get("editable_prompt") or section.get("generated_prompt"),
                "user_instruction": payload.user_instruction,
                "last_regenerated_at": datetime.datetime.utcnow().isoformat(),
                "manually_edited": False,
                "prompt_last_updated_at": datetime.datetime.utcnow().isoformat(),
            })
            break

    doc["version"] = doc.get("version", 1) + 1
    doc["updated_at"] = datetime.datetime.utcnow().isoformat()
    upsert("documents", doc)
    return {"message": "Section regenerated", "document": doc}

# -----------------
# Regenerate Page
# -----------------
@router.post("/{doc_id}/regenerate-page")
async def regenerate_page(doc_id: str, payload: RegeneratePageRequest = Body(...), user=Depends(get_current_user)):
    doc = find_by_id("documents", doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not _can_access_doc(user, doc):
        raise HTTPException(status_code=403, detail="Access denied")

    page = next((p for p in doc.get("pages", []) if p.get("name") == payload.page_name), None)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    raw_text = (payload.raw_text or doc.get("raw_text", "") or "").strip()
    try:
        author_role = (_get_user_config(user).get("created_by") or _get_user_config(user).get("document_type")) if _get_user_config(user) else None
        prompt_to_use = page.get("editable_prompt") or page.get("generated_prompt") or ai._build_page_prompt({**page, "created_by": author_role})

        ai_resp = ai.regenerate_page(
            raw_text,
            page.get("content"),
            payload.user_instruction,
            prompt_to_use
        )
    except Exception:
        logger.exception("AI regenerate_page call failed")
        ai_resp = ""

    # ✅ Safe parsing for dict, string, or plain text
    try:
        parsed = json.loads(ai_resp) if ai_resp else {}
        if isinstance(parsed, dict) and "pages" in parsed:
            new_page = (parsed.get("pages") or [{}])[0]
        elif isinstance(parsed, dict):
            new_page = parsed
        elif isinstance(parsed, str):
            try:
                new_page = json.loads(parsed)
            except Exception:
                new_page = {"content": parsed, "prompt_used": prompt_to_use}
        else:
            new_page = {"content": str(parsed), "prompt_used": prompt_to_use}
    except Exception:
        logger.exception("Failed to parse AI response while regenerating page.")
        new_page = {"content": "AI error", "prompt_used": prompt_to_use}

    for i, p in enumerate(doc.get("pages", [])):
        if p.get("name") == page.get("name"):
            doc["pages"][i].update({
                "content": new_page.get("content"),
                "prompt_used": new_page.get("prompt_used", prompt_to_use),
                "generated_prompt": page.get("generated_prompt"),
                "editable_prompt": page.get("editable_prompt") or page.get("generated_prompt"),
                "user_instruction": payload.user_instruction,
                "last_regenerated_at": datetime.datetime.utcnow().isoformat(),
                "manually_edited": False,
                "prompt_last_updated_at": datetime.datetime.utcnow().isoformat(),
            })
            break

    doc["version"] = doc.get("version", 1) + 1
    doc["updated_at"] = datetime.datetime.utcnow().isoformat()
    upsert("documents", doc)
    return {"message": "Page regenerated", "document": doc}


# -----------------
# Regenerate Document
# -----------------
@router.post("/{doc_id}/regenerate-document")
async def regenerate_document(
    doc_id: str,
    payload: RegenerateDocumentRequest = Body(...),
    user=Depends(get_current_user)
):
    doc = find_by_id("documents", doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not _can_access_doc(user, doc):
        raise HTTPException(status_code=403, detail="Access denied")

    raw_text = (payload.raw_text or doc.get("raw_text", "") or "").strip()

    pages_override = []
    # get document_type from stored config (if any)
    user_config = _get_user_config(user)
    author_role = user_config.get("created_by") or user_config.get("document_type") if user_config else None

    # -----------------
    # Pages
    # -----------------
    for p in doc.get("pages", []):
        pg_copy = {
            k: p.get(k)
            for k in [
                "name",
                "sequence",
                "page_type",
                "layout",
                "instruction",
                "formatting_rules",
                "placeholders",
                "sample_output",
            ]
        }
        try:
            manually_edited = p.get("manually_edited", False)
            prev_prompt = p.get("generated_prompt")

            if manually_edited and (p.get("editable_prompt") or prev_prompt):
                # Keep user-edited
                pg_copy["generated_prompt"] = p.get("editable_prompt") or prev_prompt
            else:
                # Auto-generate fresh
                pg_copy_with_role = {**pg_copy, "created_by": author_role}
                pg_copy["generated_prompt"] = ai._build_page_prompt(pg_copy_with_role)
                pg_copy["manually_edited"] = False

            pg_copy["editable_prompt"] = p.get("editable_prompt") or pg_copy["generated_prompt"]
            pg_copy["prompt_last_updated_at"] = datetime.datetime.utcnow().isoformat()

        except Exception:
            logger.exception("Failed to build page prompt")
            pg_copy["generated_prompt"] = p.get("generated_prompt") or p.get("instruction") or ""
        pages_override.append(pg_copy)

    # -----------------
    # Sections
    # -----------------
    sections_override = []
    for s in doc.get("sections", []):
        sec_copy = {
            k: s.get(k)
            for k in [
                "name",
                "sequence",
                "type",
                "formatting_rules",
                "style_tone",
                "length_word_count",
                "sample_output",
            ]
        }
        try:
            manually_edited = s.get("manually_edited", False)
            prev_prompt = s.get("generated_prompt")

            if manually_edited and (s.get("editable_prompt") or prev_prompt):
                sec_copy["generated_prompt"] = s.get("editable_prompt") or prev_prompt
            else:
                sec_copy["generated_prompt"] = ai._build_section_prompt(sec_copy)
                sec_copy["manually_edited"] = False

            sec_copy["editable_prompt"] = s.get("editable_prompt") or sec_copy["generated_prompt"]
            sec_copy["prompt_last_updated_at"] = datetime.datetime.utcnow().isoformat()

        except Exception:
            logger.exception("Failed to build section prompt")
            sec_copy["generated_prompt"] = s.get("generated_prompt") or s.get("instruction") or ""
        sections_override.append(sec_copy)

    # -----------------
    # Call AI
    # -----------------
    try:
        ai_resp_str = ai.generate_document_from_template(
            {}, raw_text, pages_override, sections_override
        )
    except Exception:
        logger.exception("AI generate_document_from_template call failed")
        ai_resp_str = ""

    try:
        doc_json = json.loads(ai_resp_str) if ai_resp_str else {}
    except Exception:
        logger.exception("AI returned invalid JSON during regenerate_document.")
        raise HTTPException(status_code=500, detail="AI returned invalid JSON")

    doc.update(
        {
            "title": doc_json.get("title", doc.get("title")),
            "pages": doc_json.get("pages", doc.get("pages")),
            "sections": doc_json.get("sections", doc.get("sections")),
            "version": doc.get("version", 1) + 1,
            "updated_at": datetime.datetime.utcnow().isoformat(),
        }
    )
    upsert("documents", doc)
    return {"message": "Document regenerated", "document": doc}



# ---------------------------
# Export endpoint + helpers
# ---------------------------
class SectionModel(BaseModel):
    name: str
    type: Optional[str] = "text"
    content: Any = None


class ExportRequest(BaseModel):
    title: Optional[str] = "Document"
    pages: List[SectionModel] = Field(default_factory=list)
    sections: List[SectionModel] = Field(default_factory=list)



def normalize_html_content(content: str) -> str:
    """Ensure content is wrapped into valid HTML for PDF/DOCX export."""
    if not isinstance(content, str):
        content = str(content or "")

    # If frontend sent plain text (no tags), wrap into <p>
    if "<" not in content and ">" not in content:
        lines = content.split("\n")
        content = "".join(f"<p>{line.strip()}</p>" for line in lines if line.strip())

    return f"""
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{
          font-family: Arial, sans-serif;
          font-size: 12pt;
          line-height: 1.5;
          margin: 40px;
        }}
        h1, h2, h3, h4, h5, h6 {{
          font-weight: bold;
          margin-top: 20px;
          margin-bottom: 10px;
        }}
        p {{
          margin: 10px 0;
        }}
        ul, ol {{
          margin: 10px 20px;
        }}
        table {{
          border-collapse: collapse;
          width: 100%;
          margin: 15px 0;
        }}
        th, td {{
          border: 1px solid #333;
          padding: 6px;
          text-align: left;
        }}
      </style>
    </head>
    <body>
      {content}
    </body>
    </html>
    """



def create_docx_bytes_from_html(html: str) -> bytes:
    """Convert HTML string into DOCX bytes using htmldocx (preserves formatting)."""
    if not isinstance(html, str):
        html = str(html or "")

    doc = Document()
    parser = HtmlToDocx()
    parser.add_html_to_document(html, doc)

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio.read()


@router.post("/{doc_id}/export")
async def export_document(doc_id: str, request: Request):
    doc = find_by_id("documents", doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    safe_title = (doc.get("title") or f"document_{doc_id}").replace(" ", "_")
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"{safe_title}_{timestamp}.docx"

    try:
        body = await request.json()
        html_content = body.get("htmlContent") if isinstance(body, dict) else None
        if not html_content or not isinstance(html_content, str):
            raise HTTPException(status_code=400, detail="htmlContent is required for export.")

        # ✅ Trust frontend's styled HTML directly (no extra wrapping)
        styled_html = html_content.strip()

        data = create_docx_bytes_from_html(styled_html)
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers=headers
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Export failed for doc %s: %s", doc_id, e)
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Export failed on server."}
        )


# ---------------------------
# Save Section
# ---------------------------
def _normalize_content(content):
    """
    Preserve HTML/text as-is, only parse JSON if it's really JSON.
    """
    if isinstance(content, (dict, list)):
        return content
    if isinstance(content, str):
        # detect JSON-like string
        s = content.strip()
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                return json.loads(s)
            except Exception:
                return content
        return content
    return content



@router.post("/{doc_id}/save-section")
def save_section(doc_id: str, payload: dict = Body(...), user=Depends(get_current_user)):
    section_name = payload.get("section_name")
    content = payload.get("content", "")

    if not section_name:
        raise HTTPException(status_code=400, detail="section_name is required")

    doc = find_by_id("documents", doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not _can_access_doc(user, doc):
        raise HTTPException(status_code=403, detail="Access denied")

    for i, s in enumerate(doc.get("sections", [])):
        if s.get("name") == section_name:
            doc["sections"][i]["content"] = _normalize_content(content)
            doc["sections"][i]["manually_edited"] = True
            doc["sections"][i]["last_saved_at"] = datetime.datetime.utcnow().isoformat()
            break
    else:
        raise HTTPException(status_code=404, detail="Section not found")

    doc["version"] = doc.get("version", 1) + 1
    doc["updated_at"] = datetime.datetime.utcnow().isoformat()
    upsert("documents", doc)
    return {"message": "Section saved", "document": doc}


# ---------------------------
# Save Page
# ---------------------------
@router.post("/{doc_id}/save-page")
def save_page(doc_id: str, payload: dict = Body(...), user=Depends(get_current_user)):
    page_name = payload.get("page_name")
    content = payload.get("content", "")

    if not page_name:
        raise HTTPException(status_code=400, detail="page_name is required")

    doc = find_by_id("documents", doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not _can_access_doc(user, doc):
        raise HTTPException(status_code=403, detail="Access denied")

    for i, p in enumerate(doc.get("pages", [])):
        if p.get("name") == page_name:
            doc["pages"][i]["content"] = _normalize_content(content)
            doc["pages"][i]["manually_edited"] = True
            doc["pages"][i]["last_saved_at"] = datetime.datetime.utcnow().isoformat()
            break
    else:
        raise HTTPException(status_code=404, detail="Page not found")

    doc["version"] = doc.get("version", 1) + 1
    doc["updated_at"] = datetime.datetime.utcnow().isoformat()
    upsert("documents", doc)
    return {"message": "Page saved", "document": doc}
