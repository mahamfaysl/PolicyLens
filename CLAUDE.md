# CLAUDE.md

## Project

**PolicyLens**: Streamlit app + pipeline that turns institutional PDFs into source-verified structured evidence (indicators, bottlenecks, summary, briefing, outreach memo) using Gemini structured output. See README.md for user-facing docs.

## Layout

- `app.py`: UI. Results live in `st.session_state["report"]` so they survive reruns (downloads use `on_click="ignore"`). Per-session cache keyed by file SHA-256. Uses only native Streamlit widgets: no raw HTML, so model output is never injected as markup.
- `pipeline.py`: `analyze_document(pdf, client, filename, settings, progress)`. ≤ `single_pass_chars` → one `InstitutionalAudit` call; larger → page-aligned chunks run in a `ThreadPoolExecutor` (`ChunkFindings`), merged/deduped locally, then one `Synthesis` call. Failed chunks become warnings; all failing raises. `progress` is only called from the calling thread.
- `llm.py`: `GeminiClient.generate(prompt, schema) -> (parsed, model)`. Timeout, retry with backoff on 408/429/5xx, 404 marks a model unavailable, 401/403 raises `AuthError` immediately, raises `LLMError` listing every failure (nothing is swallowed). Uses `thinking_level="minimal"` for speed and drops it automatically if a model rejects it.
- `pdf_reader.py`: `read_pdf` (cleaning, encrypted/scanned detection → `DocumentError`), `chunk_document`.
- `verify.py`: checks each quote against the page text (whitespace/punctuation/hyphenation-insensitive) → `verified | page_corrected | partial | unverified | no_quote`, plus whether baseline/target numbers appear in the document.
- `schema.py`, `report.py`, `config.py`: models, Markdown/JSON export, env settings (`PL_*`).
- `tests/test_core.py`: unit tests with a fake client; no API key needed.
- `data/`: sample ADB report (15 pages).

## Commands

```bash
streamlit run app.py
pytest                      # pip install -r requirements-dev.txt
```

API key: `GEMINI_API_KEY` from `st.secrets` or the environment/`.env` (gitignored). Template in `.env.example`.

## Notes

- Model names in `config.DEFAULT_MODELS` were checked against `client.models.list()` for the project's key; re-check if calls start returning 404.
- Sample report: ~7s single-pass for 15 pages; forced map-reduce on the same file ~17s.
- Scanned PDFs are rejected (no OCR). Adding OCR via Gemini file input would be the next step.
- `.devcontainer` disables CORS/XSRF protection for Codespaces previews; don't reuse that command for a public deployment.
