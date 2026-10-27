import os
import time
from typing import Optional, List
from pypdf import PdfReader
from google import genai
from google.genai.errors import ServerError
from dotenv import load_dotenv
from schema import InstitutionalAudit

load_dotenv()

def extract_text_from_pdf(pdf_file, max_pages: int = 10) -> str:
    """Extracts text from uploaded PDF up to max_pages."""
    reader = PdfReader(pdf_file)
    extracted_text = []
    
    total_pages = min(len(reader.pages), max_pages)
    for i in range(total_pages):
        page_text = reader.pages[i].extract_text()
        if page_text:
            extracted_text.append(f"--- PAGE {i+1} ---\n{page_text}")
            
    return "\n".join(extracted_text)

def analyze_institutional_document(text: str, api_key: Optional[str] = None) -> InstitutionalAudit:
    """Extracts structured institutional audit data using current free-tier models with fallback."""
    active_key = api_key or os.getenv("GEMINI_API_KEY")
    if not active_key:
        raise ValueError("Missing Gemini API Key. Provide it via sidebar or set GEMINI_API_KEY in .env")
        
    client = genai.Client(api_key=active_key)
    
    prompt = (
        "You are an expert institutional evaluation and evidence intelligence analyst.\n"
        "Analyze the provided institutional project report, validation brief, or policy paper.\n"
        "Extract core baseline and target metrics, identify unverified data points or implementation bottlenecks, "
        "and produce an articulate, actionable executive briefing note.\n\n"
        f"Institutional Report Excerpt:\n{text[:25000]}"
    )

    models_to_try: List[str] = [
        "gemini-3.8-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
    ]
    
    last_error = None

    for model_name in models_to_try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": InstitutionalAudit,
                        "temperature": 0.2,
                    },
                )
                return response.parsed
            except ServerError as e:
                last_error = e
                time.sleep(2 * (attempt + 1))
            except Exception as e:
                last_error = e
                break

    raise RuntimeError(f"All model attempts failed. Last error: {str(last_error)}")