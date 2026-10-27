import hashlib
import logging
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from config import Settings
from llm import AuthError, GeminiClient, LLMError
from pdf_reader import DocumentError
from pipeline import analyze_document
from report import VERIFICATION_LABELS, safe_filename, to_json, to_markdown
from schema import AuditReport

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

st.set_page_config(page_title="PolicyLens | Institutional Evidence Pipeline", page_icon="📑", layout="wide")

SETTINGS = Settings.from_env()
BADGES = {"verified": "✅", "page_corrected": "✅", "partial": "🟡", "unverified": "❌", "no_quote": "➖"}


def get_api_key():
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:  # no secrets file configured
        pass
    return os.getenv("GEMINI_API_KEY")


def run_analysis(data: bytes, name: str) -> AuditReport:
    """Analyse a PDF, reusing this session's earlier result for an identical file."""
    cache = st.session_state.setdefault("cache", {})
    key = hashlib.sha256(data).hexdigest()
    if key in cache:
        return cache[key]

    client = GeminiClient(get_api_key(), SETTINGS.models, SETTINGS.timeout_s, SETTINGS.retries)
    bar = st.progress(0.0, text="Starting")
    try:
        report = analyze_document(
            data, client, name, SETTINGS, progress=lambda f, msg: bar.progress(min(f, 1.0), text=msg)
        )
    finally:
        bar.empty()
    if len(cache) >= 5:
        cache.pop(next(iter(cache)))
    cache[key] = report
    return report


def render_report(report: AuditReport):
    s, m = report.synthesis, report.meta
    st.subheader(s.project_title)

    c1, c2, c3, c4 = st.columns([3, 3, 2, 2])
    c1.metric("Institution", s.institution_name)
    c2.metric("Sector", s.sector)
    c3.metric("Indicators", f"{len(report.indicators)}", f"{report.verified_count} verified", delta_color="off")
    c4.metric("Processed in", f"{m.elapsed_s}s", f"{m.pages} pages", delta_color="off")

    stem = safe_filename(s.institution_name)
    d1, d2, _ = st.columns([2, 2, 6])
    d1.download_button("📥 Dossier (Markdown)", to_markdown(report), f"dossier_{stem}.md", "text/markdown", on_click="ignore")
    d2.download_button("📥 Data (JSON)", to_json(report), f"audit_{stem}.json", "application/json", on_click="ignore")

    for w in m.warnings:
        st.warning(w)

    overview, indicators, memo, details = st.tabs(["Overview", "Indicator matrix", "Outreach memo", "Run details"])

    with overview:
        st.markdown("#### Executive summary")
        st.write(s.executive_summary)
        left, right = st.columns(2, gap="large")
        with left:
            st.markdown("#### Core objectives")
            for o in s.core_objectives:
                st.markdown(f"- {o}")
            st.markdown("#### ⚠️ Implementation & evaluation bottlenecks")
            for b in s.implementation_bottlenecks:
                st.markdown(f"- {b}")
        with right:
            st.markdown("#### 🎯 Strategic briefing angle")
            st.info(s.stakeholder_briefing_angle)

    with indicators:
        if not report.indicators:
            st.write("No specific quantitative indicators identified.")
        else:
            st.caption(
                "Each quote is machine-checked against the PDF text. ✅ found on the cited page · 🟡 close match · "
                "❌ not found (treat with caution) · ➖ no quote."
            )
            df = pd.DataFrame(
                {
                    "": [BADGES[i.verification] for i in report.indicators],
                    "Indicator": [i.indicator_name for i in report.indicators],
                    "Baseline": [i.baseline_value or "—" for i in report.indicators],
                    "Target": [i.target_value or "—" for i in report.indicators],
                    "Page": [i.source_page for i in report.indicators],
                    "Status / evidence gap": [i.status_or_evidence_gap for i in report.indicators],
                }
            )
            st.dataframe(df, hide_index=True, width="stretch")
            for i in report.indicators:
                with st.expander(f"{BADGES[i.verification]} {i.indicator_name}  ·  p.{i.source_page or '?'}"):
                    st.markdown(f"**Evidence check:** {VERIFICATION_LABELS[i.verification]}")
                    if i.numbers_in_source is False:
                        st.warning("A figure in the baseline/target does not appear anywhere in the document text.")
                    if i.evidence_quote:
                        st.markdown(f"> {i.evidence_quote}")

    with memo:
        st.caption("Draft only: review before sending.")
        with st.container(border=True):
            st.markdown(s.tailored_outreach_memo)

    with details:
        st.json(m.model_dump())


# --- Sidebar -----------------------------------------------------------------
st.title("📑 PolicyLens: Institutional Evidence & Briefing Pipeline")
st.caption("Evidence extraction, source-verified indicators, and briefing generation for institutional reports.")

with st.sidebar:
    st.header("Document Input")
    uploaded = st.file_uploader("Upload report (PDF)", type=["pdf"])
    st.info("Any length: large reports are analysed in parallel sections.")
    run = st.button("Run Evidence Extraction", type="primary", disabled=uploaded is None)

if run and uploaded is not None:
    st.session_state.pop("report", None)
    st.session_state.pop("error", None)
    try:
        st.session_state["report"] = run_analysis(uploaded.getvalue(), uploaded.name)
    except (DocumentError, AuthError, LLMError) as e:
        st.session_state["error"] = str(e)
    except Exception:
        logging.getLogger("policylens").exception("Unexpected failure")
        st.session_state["error"] = "Unexpected error while analysing the document. See the server log for details."

# Results live in session_state, so they survive reruns (e.g. clicking a download button).
if st.session_state.get("error"):
    st.error(st.session_state["error"])
elif st.session_state.get("report"):
    render_report(st.session_state["report"])
else:
    st.info("Upload an institutional report PDF in the sidebar to begin.")
