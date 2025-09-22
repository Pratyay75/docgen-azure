# backend/app/models.py
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


# ----------------------------------------------------------------------
# SECTION CONFIGURATION
# ----------------------------------------------------------------------
class SectionDefinition(BaseModel):
    """
    Defines a section of a document as configured by the user.

    - `generated_prompt`: AI-generated prompt from fields.
    - `editable_prompt`: user-edited prompt (if manually_edited=True).
    - `prompt_used`: actual prompt sent to AI when generating content.
    - `prompt_last_updated_at`: timestamp when prompt was last updated.
    """
    name: str
    sequence: int = 0
    type: Optional[str] = "text"  # "text" | "list" | "table"
    formatting_rules: List[str] = Field(default_factory=list)

    # Descriptive fields for AI prompt generation
    style_tone: Optional[str] = None           # e.g., "Persuasive, concise, academic"
    length_word_count: Optional[str] = None   # e.g., "200-300 words"
    sample_output: Optional[str] = None       # optional example content / layout

    # 🔹 NEW: Author role (created_by replaces document_type usage)
    created_by: Optional[str] = None          # e.g., "business analyst", "research analyst"

    # Prompt fields
    generated_prompt: Optional[str] = None
    editable_prompt: Optional[str] = None
    prompt_used: Optional[str] = None
    prompt_last_updated_at: Optional[str] = None  # ISO timestamp

    # Runtime flags / validation
    mandatory: Optional[bool] = False
    manually_edited: Optional[bool] = False


# ----------------------------------------------------------------------
# PAGE CONFIGURATION
# ----------------------------------------------------------------------
class PageDefinition(BaseModel):
    """
    Defines a special 'page' in the document (cover page, declaration, certificate, bill, etc).

    - `generated_prompt`: AI-generated prompt from fields.
    - `editable_prompt`: user-edited prompt (if manually_edited=True).
    - `prompt_used`: actual prompt sent to AI when generating content.
    - `prompt_last_updated_at`: timestamp when prompt was last updated.
    """
    name: str                               # e.g. "Cover Page", "Declaration"
    sequence: int = 0                       # page order (before sections)
    page_type: Optional[str] = "other"      # "cover" | "declaration" | "certificate" | "bill" | "policy" | "other"
    layout: Optional[str] = "text"          # "text" | "table" | "list" | "mixed"

    # Core AI content generation fields
    instruction: Optional[str] = None       # e.g., "Generate a formal declaration page..."
    formatting_rules: List[str] = Field(default_factory=list)  # styling rules
    placeholders: Optional[Dict[str, str]] = None              # dynamic placeholders
    sample_output: Optional[str] = None     # optional example snippet / layout

    # 🔹 NEW: Author role (created_by replaces document_type usage)
    created_by: Optional[str] = None        # e.g., "business analyst", "research analyst"

    # Prompt handling
    generated_prompt: Optional[str] = None
    editable_prompt: Optional[str] = None
    prompt_used: Optional[str] = None
    prompt_last_updated_at: Optional[str] = None  # ISO timestamp
    manually_edited: Optional[bool] = False


# ----------------------------------------------------------------------
# DOCUMENT GENERATION REQUESTS
# ----------------------------------------------------------------------
class CreateDocumentRequest(BaseModel):
    """
    Request payload when generating a new document.

    Supports both pages (new) and sections (existing).
    """
    template_id: Optional[str] = None
    raw_text: Optional[str] = None           # raw extracted text from upload
    pages: Optional[List[PageDefinition]] = None
    sections: Optional[List[SectionDefinition]] = None

    # Deprecated
    editable_prompt: Optional[str] = None
    title: Optional[str] = None


class RegenerateSectionRequest(BaseModel):
    """Request payload when regenerating a single section."""
    section_name: str
    raw_text: Optional[str] = None
    user_instruction: Optional[str] = None   # replaces editable_prompt
    base_prompt: Optional[str] = None        # new: to send correct base prompt


class RegeneratePageRequest(BaseModel):
    """Request payload when regenerating a single page."""
    page_name: str
    raw_text: Optional[str] = None
    user_instruction: Optional[str] = None
    base_prompt: Optional[str] = None        # new: to send correct base prompt


class RegenerateDocumentRequest(BaseModel):
    """
    Request payload when regenerating the entire document.

    In the new flow:
    - Global prompt is ignored.
    - Pages are generated first, then sections.
    """
    raw_text: Optional[str] = None
    sections_prompts: Optional[Dict[str, str]] = None
    pages_prompts: Optional[Dict[str, str]] = None


# ----------------------------------------------------------------------
# USER MODELS
# ----------------------------------------------------------------------
class UserCreate(BaseModel):
    """Request payload to create a new user."""
    email: str
    password: str
    name: Optional[str] = None
    role: Optional[str] = "user"  # "user" | "admin" | "superadmin"


class UserOut(BaseModel):
    """Response model for user details (excludes password)."""
    id: str
    email: str
    name: Optional[str]
    role: str


# ----------------------------------------------------------------------
# TEMPLATE & CONFIG
# ----------------------------------------------------------------------
class Template(BaseModel):
    """Document template with predefined sections."""
    id: str
    title: str
    sections: List[SectionDefinition] = Field(default_factory=list)

    # Deprecated
    editable_prompt: Optional[str] = None


class UserConfig(BaseModel):
    """
    Stores a user’s saved configuration of pages + sections.

    Each page/section includes descriptive fields + auto-generated prompt.
    """
    id: Optional[str] = None       # typically set to user.id
    user_id: Optional[str] = None
    title: Optional[str] = None

    # 🔹 NEW: Document-level configuration
    document_name: Optional[str] = None
    created_by: Optional[str] = None        # e.g. "business analyst", "research analyst"

    # Deprecated (kept for backward compatibility)
    document_type: Optional[str] = None     # legacy field, use created_by instead

    # Configured Pages (appear before sections)
    pages: List[PageDefinition] = Field(default_factory=list)

    # Configured Sections
    sections: List[SectionDefinition] = Field(default_factory=list)

    # Deprecated
    editable_prompt: Optional[str] = None

    updated_at: Optional[str] = None  # ISO timestamp string
