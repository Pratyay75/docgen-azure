# backend/app/ai.py
import os
import json
import logging
import re
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# -----------------------
# Logger
# -----------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------
# Environment
# -----------------------
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2023-09-01-preview")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# -----------------------
# Client Initialization
# -----------------------
client = None
use_azure = False
try:
    from openai import AzureOpenAI, OpenAI

    if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT:
        client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_API_VERSION,
        )
        use_azure = True
        logger.info("[AI] Using Azure OpenAI deployment: %s", AZURE_OPENAI_DEPLOYMENT)
    elif OPENAI_API_KEY:
        client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("[AI] Using OpenAI client (non-Azure)")
    else:
        logger.warning("[AI] No API keys found. AI client disabled.")
except Exception as e:
    logger.warning("[AI] Failed to import OpenAI SDK: %s", e)


# =====================================================
# ROLE INFERENCE (legacy, kept for fallback)
# =====================================================
def _infer_role(doc_type: str, fallback: str = "document specialist") -> str:
    """
    Infer a role (like business analyst, research analyst, etc.)
    based on document_type. Fallback to 'document specialist'.
    """
    if not doc_type:
        return fallback

    dt = doc_type.lower()
    if "business" in dt:
        return "business analyst"
    if "research" in dt or "report" in dt:
        return "research analyst"
    if "policy" in dt:
        return "policy drafting expert"
    if "bill" in dt or "legal" in dt:
        return "legal expert"
    if "certificate" in dt:
        return "certificate designer"
    if "cover" in dt:
        return "cover page specialist"
    if "declaration" in dt:
        return "declaration writer"

    # default: just use the doc_type as role
    return f"{dt} specialist"


# =====================================================
# PROMPT BUILDERS
# =====================================================
def _build_section_prompt(section: dict) -> str:
    """Build a structured, detailed prompt for a Section."""
    name = section.get("name", "Section")
    sequence = section.get("sequence", 0)
    stype = section.get("type", "text")
    style = section.get("style_tone") or "Professional"
    formatting_rules = section.get("formatting_rules") or []
    length_wc = section.get("length_word_count") or "No specific limit"
    sample_out = section.get("sample_output")
    author_role = (section.get("created_by") or section.get("document_type") or "document specialist").strip()
    document_title = section.get("document_title") or "Untitled Document"

    formatting_text = "\n".join(
        [f"• {rule}" for rule in formatting_rules]
    ) if formatting_rules else "• No special formatting"

    sample_text = (
        f"This is ONLY a structural/layout hint. Do NOT copy text:\n{sample_out}"
        if sample_out else "None provided"
    )

    return f"""
You are an experienced {author_role} tasked with drafting professional documentation. 
Your role is to write from the perspective of a {author_role}, ensuring clarity, structure, and relevance to the intended audience.

Generate ONLY the content for the section "{name}" of the document "{document_title}" with the following constraints:

- Sequence: {sequence}
- Section Type: {stype}
- Style & Tone: {style}
- Formatting Rules: {formatting_text}
- Target Length: {length_wc}

### Writing Instructions:
1. Use the uploaded raw content as the **only source of facts/text**.  
2. Ensure the content is relevant to the section purpose.  
3. Use the style and tone specified above.  
4. Structure the output according to the section type (e.g., list, text, table).  
5. Respect formatting rules strictly.  
6. Do not include extra sections, titles, or explanations.  

### Structural Example (Optional):
{sample_text}  

### Notes:
Keep the response strictly limited to the section content. Do not add commentary or labels.
### :
- Output MUST be valid HTML.
- For text → wrap in <p>, <h2>, <strong>, <em>, etc.
- For lists → use <ul><li>…</li></ul>.
- For tables → use <table><tr><th>..</th></tr><tr><td>..</td></tr></table>.
- Do NOT output plain JSON here, only HTML inside "content".
- Do not add commentary, labels, or explanations.

""".strip()


def _build_page_prompt(page: dict) -> str:
    """Build a structured, editable multi-prompt for a Page."""
    name = page.get("name", "Page")
    sequence = page.get("sequence", 0)
    ptype = page.get("page_type", "other")
    layout = page.get("layout", "text")
    instruction = page.get("instruction") or ""
    formatting_rules = page.get("formatting_rules") or []
    sample_out = page.get("sample_output")
    author_role = (page.get("created_by") or page.get("document_type") or "document specialist").strip()
    document_title = page.get("document_title") or "Untitled Document"
    purpose = page.get("purpose") or ""
    writing_instructions = page.get("writing_instructions") or "formal"
    length = page.get("length_wordcount") or "No specific limit"
    notes = page.get("notes") or ""

    formatting_text = (
        "\n".join([f"• {rule}" for rule in formatting_rules])
        if formatting_rules else "• No special formatting"
    )

    sample_text = (
        f"This is ONLY a structural/layout hint. Do NOT copy text:\n{sample_out}"
        if sample_out else "None provided"
    )

    return f"""
You are an experienced {author_role} tasked with drafting professional documentation. 
Your role is to write from the perspective of a {author_role}, ensuring clarity, structure, and relevance to the intended audience.  

Generate ONLY the content for the page "{name}" with the following constraints:  

- Sequence: {sequence}  
- Page Type: {ptype}  
- Layout: {layout}  
- Document Title: {document_title}  

### Writing Objectives:
1. Use the uploaded raw content as the **only source of facts/text**.  
2. Clearly explain the purpose of this page in context of the full document.  
3. Use language suitable for a professional business/technical audience.  
4. Maintain consistency in tone with typical {author_role} deliverables.  
5. Keep content concise but meaningful (avoid unnecessary filler).  

### Formatting Rules:
{formatting_text}  

### Content Guidance:
- *Purpose of this Page*: {purpose}  
- *Specific Instructions*: {instruction or "To be defined"}  
- *Writing Style*: {writing_instructions}  
- *Length Guidance*: Target {length}  

### Structural Example (Optional):  
{sample_text}  

### Notes: 
### :
- Output MUST be valid HTML.
- For text → wrap in <p>, <h1>, <h2>, <strong>, <em>, etc.
- For lists → use <ul><li>…</li></ul>.
- For tables → use <table><tr><th>..</th></tr><tr><td>..</td></tr></table>.
- Do NOT output plain JSON here, only HTML inside "content".
- Do not add commentary, labels, or explanations.
{notes}
""".strip()


# =====================================================
# HELPERS
# =====================================================
def _strip_leading_heading(html_or_text: str, force: bool = False) -> str:
    """
    Optionally strip leading <h1>/<h2> headings.
    - By default, KEEP user formatting (do not strip).
    - If force=True, we strip (used only in auto-generated AI text cleanup).
    """
    if not isinstance(html_or_text, str):
        return html_or_text
    if not force:
        return html_or_text  # ✅ keep manual formatting
    text = re.sub(r"^\s*<h[1-6][^>]*>.*?</h[1-6]>\s*", "", html_or_text, flags=re.I | re.S)
    text = re.sub(r"^\s*[A-Z0-9 ,\-\_]{3,}\n[-=]{3,}\s*", "", text)
    return text


def _safe_json_loads(s: str):
    """Try to parse string into dict, else return {}."""
    if not s:
        return {}
    try:
        return json.loads(s)
    except Exception:
        return {}

# (rest of your file remains unchanged)
# =====================================================
# (keep your _sanitize_and_fill, generate_document_from_template,
#  regenerate_section, regenerate_page exactly as they are)
# =====================================================
# (your sanitize, generate, and regenerators stay same — no SyntaxError issues there)



# (rest of your file remains unchanged)
# =====================================================
# (keep your _sanitize_and_fill, generate_document_from_template,
#  regenerate_section, regenerate_page exactly as they are)


# (rest of your file remains unchanged)

def _sanitize_and_fill(content, template, pages_override, sections_override):
    """Ensure valid JSON structure and fill missing prompts/content."""
    try:
        data = _safe_json_loads(content) if isinstance(content, str) else (content or {})
        if not isinstance(data, dict):
            data = {}


        if not data.get("title"):
            data["title"] = (
                template.get("title") if isinstance(template, dict) else "Generated Document"
            )

        # Pages
        valid_page_names = {p.get("name") for p in (pages_override or [])}
        pages = data.get("pages", [])
        if valid_page_names:
            pages = [pg for pg in pages if pg.get("name") in valid_page_names]

        sanitized_pages = []
        for pg in pages_override:  # keep config order
            match = next((x for x in pages if x.get("name") == pg.get("name")), {})
            merged = {**pg, **match}
            if not merged.get("generated_prompt"):
                merged["generated_prompt"] = _build_page_prompt(pg)
            if not merged.get("prompt_used"):
                merged["prompt_used"] = merged.get("editable_prompt") or merged["generated_prompt"]
            if not merged.get("content"):
                merged["content"] = f"⚠️ No content generated for {pg.get('name','Page')}."
            merged["prompt_last_updated_at"] = datetime.utcnow().isoformat()
            sanitized_pages.append(merged)
        data["pages"] = sanitized_pages

        # Sections
        valid_names = {s.get("name") for s in (sections_override or [])}
        secs = data.get("sections", [])
        if valid_names:
            secs = [sec for sec in secs if sec.get("name") in valid_names]

        sanitized_secs = []
        for sec in sections_override:  # keep config order
            match = next((x for x in secs if x.get("name") == sec.get("name")), {})
            merged = {**sec, **match}
            if not merged.get("generated_prompt"):
                merged["generated_prompt"] = _build_section_prompt(sec)
            if not merged.get("prompt_used"):
                merged["prompt_used"] = merged.get("editable_prompt") or merged["generated_prompt"]

            content_val = merged.get("content")
            if isinstance(content_val, str):
    # ✅ Keep AI HTML output as-is, only clean leading redundant headings
            # ✅ Keep AI HTML exactly as-is, don’t strip headings
                cleaned = _strip_leading_heading(content_val, force=False).strip()
                merged["content"] = cleaned or f"⚠️ No content generated for {sec.get('name','Section')}."
    


            elif content_val is None or (isinstance(content_val, (list, dict)) and not content_val):
                if sec.get("type") == "list":
                    merged["content"] = [f"{sec['name']} point 1", f"{sec['name']} point 2"]
                elif sec.get("type") == "table":
                    merged["content"] = [{"Column": "Example", "Value": "Sample"}]
                else:
                    merged["content"] = f"⚠️ No content generated for {sec.get('name','Section')}."
            merged["prompt_last_updated_at"] = datetime.utcnow().isoformat()
            sanitized_secs.append(merged)

        data["sections"] = sanitized_secs
        return json.dumps(data, ensure_ascii=False)

    except Exception as e:
        logger.error("[AI] Failed to sanitize AI response: %s", e, exc_info=True)
        # fallback basic doc
        return json.dumps(
            {
                "title": "Generated Document",
                "pages": [
                    {
                        "name": p.get("name", "Page"),
                        "sequence": p.get("sequence", 0),
                        "layout": p.get("layout", "text"),
                        "instruction": p.get("instruction"),
                        "generated_prompt": _build_page_prompt(p),
                        "prompt_used": _build_page_prompt(p),
                        "content": f"⚠️ Content could not be generated for {p.get('name','Page')}."
                    }
                    for p in (pages_override or [])
                ],
                "sections": [
                    {
                        "name": s.get("name", "Section"),
                        "sequence": s.get("sequence", 0),
                        "type": s.get("type", "text"),
                        "generated_prompt": _build_section_prompt(s),
                        "prompt_used": _build_section_prompt(s),
                        "content": f"⚠️ Content could not be generated for {s.get('name','Section')}."
                    }
                    for s in (sections_override or [])
                ]
            },
            ensure_ascii=False
        )


# =====================================================
# MAIN GENERATION
# =====================================================
def generate_document_from_template(template: dict, raw_text: str, pages_override: list = None, sections_override: list = None) -> str:
    """Generate a document by sequentially building each page/section."""
    logger.info("[AI] generate_document_from_template called; raw_text length=%d", len(raw_text or ""))
    pages_override = pages_override or []
    sections_override = sections_override or []

    pages_out, sections_out = [], []

    def _call_ai_for_item(role, item_name, prompt_text, raw_text_context):
        if not client:
            snippet = (raw_text_context or "")[:120].replace("\n", " ")
            return {"name": item_name, "content": f"⚠️ Placeholder for {item_name}: {snippet}", "generated_prompt": prompt_text, "prompt_used": prompt_text}

        system_msg = "You are a page generator. Return only the page content." if role == "page" else \
                     "You are a section generator. Return only the section content."

        try:
            resp = client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT if use_azure else "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": json.dumps({"name": item_name, "prompt": prompt_text, "raw_text": raw_text_context}, ensure_ascii=False)},
                ],
                temperature=0.25,
            )
            content = resp.choices[0].message.content
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "content" in parsed:
                    return {"name": item_name, "content": parsed["content"], "generated_prompt": prompt_text, "prompt_used": prompt_text}
                return {"name": item_name, "content": content, "generated_prompt": prompt_text, "prompt_used": prompt_text}
            except Exception:
                return {"name": item_name, "content": content, "generated_prompt": prompt_text, "prompt_used": prompt_text}
        except Exception as e:
            logger.exception("[AI] single-item generation failed for %s '%s': %s", role, item_name, e)
            return {"name": item_name, "content": f"⚠️ AI generation failed for {item_name}", "generated_prompt": prompt_text, "prompt_used": prompt_text}

    # Pages: prefer latest editable/generated prompt
    for p in pages_override:
        prompt_to_use = p.get("editable_prompt") or p.get("generated_prompt") or _build_page_prompt(p)
        out = _call_ai_for_item("page", p.get("name"), prompt_to_use, raw_text)
        out.setdefault("sequence", p.get("sequence", 0))
        out["prompt_last_updated_at"] = datetime.utcnow().isoformat()
        pages_out.append({**p, **out})

    # Sections: prefer latest editable/generated prompt
    for s in sections_override:
        prompt_to_use = s.get("editable_prompt") or s.get("generated_prompt") or _build_section_prompt(s)
        out = _call_ai_for_item("section", s.get("name"), prompt_to_use, raw_text)
        if isinstance(out.get("content"), str):
    # ✅ Preserve headings, just trim whitespace
            out["content"] = _strip_leading_heading(out["content"], force=False).strip()


        out.setdefault("sequence", s.get("sequence", 0))
        out["prompt_last_updated_at"] = datetime.utcnow().isoformat()
        sections_out.append({**s, **out})

    doc_obj = {
        "title": template.get("title") if isinstance(template, dict) else "Generated Document",
        "pages": pages_out,
        "sections": sections_out,
    }

    return _sanitize_and_fill(json.dumps(doc_obj, ensure_ascii=False), template, pages_override, sections_override)

# =====================================================
# REGENERATORS
# =====================================================
def regenerate_section(raw_text: str, existing_content: str, user_instruction: str, base_prompt: str) -> str:
    """
    Regenerate a document section based on existing content, raw_text context, and user instruction.
    Always returns valid JSON with a "sections" key.
    """
    if not client:
        clean = _strip_leading_heading(existing_content or "")
        return json.dumps({"sections": [{
            "name": "Regenerated Section",
            "content": f"{clean} (modified with {user_instruction})",
            "prompt_used": f"{base_prompt} + {user_instruction}",
            "generated_prompt": base_prompt,
        }]}, ensure_ascii=False)

    try:
        resp = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT if use_azure else "gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an assistant that rewrites document SECTIONS.\n"
                        "Rewrite ONLY the provided existing_content using raw_text as context.\n"
                        "Strictly apply the user_instruction.\n"
                        "Return valid JSON with a top-level key 'sections'.\n"
                        "Each section must include: name, content, prompt_used, generated_prompt."
                    )
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "raw_text": raw_text,
                        "existing_content": existing_content,
                        "user_instruction": user_instruction,
                        "base_prompt": base_prompt
                    }, ensure_ascii=False),
                },
            ],
            temperature=0.3,
        )

        ai_out = resp.choices[0].message.content.strip()
        logger.info("[AI][regenerate_section] raw output: %s", ai_out)

        parsed = _safe_json_loads(ai_out)
        if parsed and "sections" in parsed and parsed["sections"]:
            # clean content
            parsed["sections"][0]["content"] = _strip_leading_heading(
                parsed["sections"][0].get("content", ""), force=False
            ).strip() or existing_content


        # fallback if plain text
        return json.dumps({"sections": [{
            "name": "Regenerated Section",
            "content": _strip_leading_heading(ai_out or existing_content or "⚠️ No content"),
            "prompt_used": f"{base_prompt} + {user_instruction}",
            "generated_prompt": base_prompt,
        }]}, ensure_ascii=False)

    except Exception as e:
        logger.exception("[AI] regenerate_section failed: %s", e)
        return json.dumps({"sections": [{
            "name": "Regenerated Section",
            "content": f"{existing_content or '⚠️ AI error'} (modified with {user_instruction})",
            "prompt_used": f"{base_prompt} + {user_instruction}",
            "generated_prompt": base_prompt,
        }]}, ensure_ascii=False)


def regenerate_page(raw_text: str, existing_content: str, user_instruction: str, base_prompt: str) -> str:
    """
    Regenerate a document page based on existing content, raw_text context, and user instruction.
    Always returns valid JSON with a "pages" key.
    """
    if not client:
        return json.dumps({"pages": [{
            "name": "Regenerated Page",
            "content": f"{existing_content} (modified with {user_instruction})",
            "prompt_used": f"{base_prompt} + {user_instruction}",
            "generated_prompt": base_prompt,
        }]}, ensure_ascii=False)

    try:
        resp = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT if use_azure else "gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an assistant that rewrites document PAGES.\n"
                        "Rewrite ONLY the provided existing_content using raw_text as context.\n"
                        "Strictly apply the user_instruction.\n"
                        "Return valid JSON with a top-level key 'pages'.\n"
                        "Each page must include: name, content, prompt_used, generated_prompt."
                    )
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "raw_text": raw_text,
                        "existing_content": existing_content,
                        "user_instruction": user_instruction,
                        "base_prompt": base_prompt
                    }, ensure_ascii=False),
                },
            ],
            temperature=0.3,
        )

        ai_out = resp.choices[0].message.content.strip()
        logger.info("[AI][regenerate_page] raw output: %s", ai_out)

        parsed = _safe_json_loads(ai_out)
        if parsed and "pages" in parsed and parsed["pages"]:
            parsed["pages"][0]["content"] = parsed["pages"][0].get("content", "").strip() or existing_content
            return json.dumps(parsed, ensure_ascii=False)

        # fallback if plain text
        return json.dumps({"pages": [{
            "name": "Regenerated Page",
            "content": ai_out or existing_content or "⚠️ No content",
            "prompt_used": f"{base_prompt} + {user_instruction}",
            "generated_prompt": base_prompt,
        }]}, ensure_ascii=False)

    except Exception as e:
        logger.exception("[AI] regenerate_page failed: %s", e)
        return json.dumps({"pages": [{
            "name": "Regenerated Page",
            "content": f"{existing_content or '⚠️ AI error'} (modified with {user_instruction})",
            "prompt_used": f"{base_prompt} + {user_instruction}",
            "generated_prompt": base_prompt,
        }]}, ensure_ascii=False)
