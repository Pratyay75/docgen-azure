# backend/app/ocr.py
import os
from dotenv import load_dotenv
load_dotenv()

AZ_FORM_ENDPOINT = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
AZ_FORM_KEY = os.getenv("AZURE_FORM_RECOGNIZER_KEY")

def extract_text_with_azure(file_path: str) -> str:
    # Try Azure Document Intelligence (prebuilt-read). Fallback to pytesseract or raw read.
    if AZ_FORM_ENDPOINT and AZ_FORM_KEY:
        try:
            from azure.ai.formrecognizer import DocumentAnalysisClient
            from azure.core.credentials import AzureKeyCredential
            client = DocumentAnalysisClient(AZ_FORM_ENDPOINT, AzureKeyCredential(AZ_FORM_KEY))
            with open(file_path, "rb") as f:
                poller = client.begin_analyze_document("prebuilt-read", document=f)
                result = poller.result()
            lines = []
            for page in getattr(result, "pages", []):
                for line in getattr(page, "lines", []):
                    lines.append(line.content)
            text = "\n".join(lines).strip()
            if text:
                return text
        except Exception:
            pass

    try:
        from PIL import Image
        import pytesseract
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img)
        if text and text.strip():
            return text.strip()
    except Exception:
        pass

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            return content.strip()
    except Exception:
        pass

    return ""
