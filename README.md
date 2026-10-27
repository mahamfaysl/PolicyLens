# PolicyLens 📑

An automated pipeline and dashboard for extracting auditable metrics, evaluation benchmarks, and strategic briefings from unstructured institutional reports (Multilateral Development Banks, Public Sector Agencies, and Policy Briefs).

---

## Overview

Public sector policy briefs and Multilateral Development Bank (MDB) completion reports are typically dense, unstructured 50+ page PDFs. Extracting verifiable indicators, tracking baseline-to-target deltas, and identifying institutional bottlenecks requires significant manual effort.

**PolicyLens** automates this workflow:
1. **Document Ingestion:** Parses high-density institutional PDFs using `pypdf`.
2. **Schema-Constrained Extraction:** Utilizes LLM function calling with strict `Pydantic` schemas to extract quantitative target metrics, implementation roadblocks, and lead stakeholder identities.
3. **Strategic Synthesis & GTM Dossier:** Converts parsed evidence into an actionable briefing memo and outreach draft tailored to the institution's stated operational gaps.
4. **Interactive Review Interface:** A dual-column Streamlit workspace designed for rapid evaluation and dossier export.

---

## Architecture & Data Flow

```text
[ Institutional PDF Report ]
              │
              ▼
    [ pypdf Text Ingestion ]
              │
              ▼
  [ Gemini Structured Outputs ]  <───  Enforced by Pydantic Schema
              │
       ┌──────┴──────┐
       ▼             ▼
[ Audit Matrix ] [ Strategic Dossier ]
(Metrics & Risks) (Engagement Memo)
       │             │
       └──────┬──────┘
              ▼
  [ Streamlit Executive UI ]