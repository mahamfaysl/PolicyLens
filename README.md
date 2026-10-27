# PolicyLens 📑

Turn long, unstructured institutional reports (development-bank completion reports, policy briefs, technical assistance documents) into **structured, source-verified evidence** and a ready-to-use briefing, in seconds.

## What it does

1. **Reads any PDF**: every page, not just the first few. Documents up to ~150k characters (~100 pages) are analysed in a single call; larger ones are split into page-aligned sections, analysed **in parallel**, then synthesised.
2. **Extracts structured data** with Gemini structured output and Pydantic schemas: indicators (baseline, target, status/gap, source page, verbatim quote), objectives, bottlenecks, executive summary, briefing angle, outreach memo.
3. **Verifies evidence automatically**: every quote the model cites is checked against the PDF text (✅ verified, 🟡 partial, ❌ not found), and every figure in a baseline/target is checked to exist in the document. Hallucinations are flagged, not hidden.
4. **Exports** a Markdown dossier and a JSON file; results persist on screen while you download.

```
PDF ─► pdf_reader ─► (≤150k chars) ─► 1 Gemini call ───────────────┐
                 └─► (larger) ─► N parallel section calls ─► merge ─► synthesis call ─┤
                                                                      verify.py ◄──────┘
                                                                          │
                                                          Streamlit UI · Markdown · JSON
```

## Run it

```bash
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env           # add GEMINI_API_KEY
streamlit run app.py
```

On Streamlit Cloud, set `GEMINI_API_KEY` in app secrets instead of `.env`.

## Configuration

All optional; see [.env.example](.env.example). Models are tried in order with retries and backoff, so a rate-limited or unavailable model falls back automatically (`PL_MODELS`).

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests need no API key (the model is faked).

## Limits to know about

- Scanned (image-only) PDFs have no text layer and are rejected with a clear message; OCR them first.
- Output is AI-generated. The verification column tells you which quotes are traceable to the source; always review figures before external use.
- Uploaded documents are sent to the Gemini API; do not use with data that may not leave your organisation.

## Layout

| File | Role |
|---|---|
| `app.py` | Streamlit UI |
| `pipeline.py` | Single-pass and parallel map-reduce orchestration |
| `llm.py` | Gemini client: timeouts, retries, model fallback, clear errors |
| `pdf_reader.py` | Text extraction, cleaning, page-aware chunking |
| `verify.py` | Evidence verification against the source |
| `schema.py` | Pydantic models |
| `report.py` | Markdown/JSON export |
| `config.py` | Settings from environment |
