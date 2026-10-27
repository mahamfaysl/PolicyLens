import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from pipeline import extract_text_from_pdf, analyze_institutional_document

load_dotenv()

st.set_page_config(
    page_title="PolicyLens | Institutional Evidence Pipeline",
    page_icon="📑",
    layout="wide"
)

# Custom Styling for polished executive feel
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    .metric-title {
        font-size: 0.82rem;
        color: #6c757d;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-top: 4px;
        line-height: 1.3;
    }
    .memo-box {
        background-color: #f1f5f9;
        border-left: 4px solid #2563eb;
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        font-size: 0.95rem;
        line-height: 1.6;
        color: #1e293b;
    }
</style>
""", unsafe_allow_html=True)

st.title("📑 PolicyLens: Institutional Evidence & Briefing Pipeline")
st.caption("Automated audit extraction, benchmark verification, and strategic briefing generation for unstructured institutional reports.")

# Helper to automatically resolve API key from Secrets or .env
def get_active_api_key():
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    return os.getenv("GEMINI_API_KEY")

api_key = get_active_api_key()

# Clean Sidebar: Document Input Only
with st.sidebar:
    st.header("Document Input")
    uploaded_file = st.file_uploader("Upload Institutional Report (PDF)", type=["pdf"])
    st.info("Supported: MDB Completion Reports, Policy Matrices, or Technical Assistance Briefs.")

if uploaded_file:
    if st.sidebar.button("Run Evidence Extraction", type="primary"):
        if not api_key:
            st.error("API Key not found. Please configure GEMINI_API_KEY in Streamlit Secrets or .env.")
        else:
            with st.spinner("Extracting text and synthesizing audit evidence..."):
                try:
                    pdf_text = extract_text_from_pdf(uploaded_file)
                    audit_result = analyze_institutional_document(pdf_text, api_key=api_key)
                    
                    st.success("Analysis complete!")
                    
                    # Top Full-Width Metric Banner
                    col1, col2, col3 = st.columns([4, 4, 2])
                    with col1:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-title">Target Institution</div>
                            <div class="metric-value">{audit_result.institution_name}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-title">Focus Sector</div>
                            <div class="metric-value">{audit_result.sector}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col3:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-title">Indicators Evaluated</div>
                            <div class="metric-value">{len(audit_result.tracked_indicators)} Tracked</div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("---")

                    # High-Impact 2-Column Split: Evidence on Left, GTM Strategy on Right
                    left_col, right_col = st.columns([1.1, 0.9], gap="large")

                    with left_col:
                        st.subheader("📊 Indicator Verification Matrix")
                        if audit_result.tracked_indicators:
                            for idx, ind in enumerate(audit_result.tracked_indicators, 1):
                                with st.expander(f"**Metric {idx}:** {ind.indicator_name}", expanded=True):
                                    st.markdown(f"**Baseline:** `{ind.baseline_value or 'Not specified'}`")
                                    st.markdown(f"**Target:** `{ind.target_value or 'Not specified'}`")
                                    st.markdown(f"**Evidence / Data Gap:** {ind.status_or_evidence_gap}")
                        else:
                            st.write("No specific quantitative indicators identified.")

                        st.markdown("### ⚠️ Implementation & Evaluation Bottlenecks")
                        for bottleneck in audit_result.implementation_bottlenecks:
                            st.markdown(f"• {bottleneck}")

                    with right_col:
                        st.subheader("🎯 Strategic Briefing Angle")
                        st.info(audit_result.stakeholder_briefing_angle)

                        st.subheader("✉️ High-Context Outreach Memo")
                        st.caption("Human-ready outreach referencing specific indicators, partners, and allocations.")
                        st.markdown(f"""
                        <div class="memo-box">
                            {audit_result.tailored_outreach_memo}
                        </div>
                        """, unsafe_allow_html=True)

                        dossier_md = f"""# PolicyLens Dossier: {audit_result.institution_name}
**Project:** {audit_result.project_title}
**Sector:** {audit_result.sector}

## Strategic Briefing Angle
{audit_result.stakeholder_briefing_angle}

## Generated Stakeholder Outreach Memo
{audit_result.tailored_outreach_memo}

## Key Bottlenecks
""" + "\n".join([f"- {b}" for b in audit_result.implementation_bottlenecks])

                        st.download_button(
                            label="📥 Download Dossier (Markdown)",
                            data=dossier_md,
                            file_name=f"dossier_{audit_result.institution_name.lower().replace(' ', '_')}.md",
                            mime="text/markdown"
                        )
                        
                except Exception as e:
                    st.error(f"Error during analysis: {str(e)}")
else:
    st.info("Upload an institutional report PDF in the sidebar to begin.")