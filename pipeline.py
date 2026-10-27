import os
import time
from typing import Optional
from pypdf import PdfReader
from google import genai
from google.genai.errors import ServerError
from dotenv import load_dotenv
from schema import InstitutionalAudit

load_dotenv()

def extract_text_from_pdf(pdf_file, max_pages: int = 5) -> str:
    """Extracts text from target early pages where indicators and budgets live."""
    reader = PdfReader(pdf_file)
    extracted_text = []
    
    # Process up to 5 core pages for instant turnaround
    total_pages = min(len(reader.pages), max_pages)
    for i in range(total_pages):
        page_text = reader.pages[i].extract_text()
        if page_text:
            extracted_text.append(f"--- PAGE {i+1} ---\n{page_text}")
            
    return "\n".join(extracted_text)

def analyze_institutional_document(text: str, api_key: Optional[str] = None) -> InstitutionalAudit:
    """Fast extraction using lightweight flash-lite endpoint."""
    active_key = api_key or os.getenv("GEMINI_API_KEY")
    if not active_key:
        raise ValueError("Missing Gemini API Key.")
        
    client = genai.Client(api_key=active_key)
    
    prompt = (
        "You are an expert institutional evaluation and evidence intelligence analyst.\n"
        "Analyze the provided institutional project report excerpt.\n"
        "Extract core baseline and target metrics, identify implementation bottlenecks, "
        "and produce an articulate, actionable executive briefing note.\n\n"
        f"Institutional Report Excerpt:\n{text[:14000]}"
    )

    # Use flash-lite as primary for 3-5x faster response times
    fast_models = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash"]

    for model_name in fast_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": InstitutionalAudit,
                    "temperature": 0.1,
                },
            )
            return response.parsed
        except Exception:
            continue

    raise RuntimeError("Unable to process document. Please try again.")