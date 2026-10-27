"""Pydantic models: what the LLM is asked to return, and what the app reports."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ExtractedIndicator(BaseModel):
    indicator_name: str = Field(description="Name or metric of the tracked indicator")
    baseline_value: Optional[str] = Field(None, description="Stated baseline or starting benchmark")
    target_value: Optional[str] = Field(None, description="Target goal or outcome benchmark")
    status_or_evidence_gap: str = Field(description="Observed status, data gap, delay, or measurement challenge")
    source_page: Optional[int] = Field(
        None, description="Page number (from the '--- PAGE n ---' markers) where the evidence appears"
    )
    evidence_quote: Optional[str] = Field(
        None,
        description="Short verbatim quote (under 200 characters) copied exactly from the source text that supports this indicator",
    )


class ChunkFindings(BaseModel):
    """Per-chunk extraction used for large documents (map step)."""

    core_objectives: List[str] = Field(description="Primary objectives stated in this excerpt, if any")
    tracked_indicators: List[ExtractedIndicator] = Field(description="Indicators found in this excerpt")
    implementation_bottlenecks: List[str] = Field(description="Operational, monitoring, or institutional bottlenecks in this excerpt")


class Synthesis(BaseModel):
    """Document-level synthesis (reduce step)."""

    institution_name: str = Field(description="Executing agency or institution (e.g., Asian Development Bank, World Bank)")
    project_title: str = Field(description="Title of the project, program, or policy initiative")
    sector: str = Field(description="Core sector (e.g., Energy Transition, Public Governance, Digital Infrastructure)")
    executive_summary: str = Field(description="A 4-6 sentence plain-language summary of what the document is and concludes")
    core_objectives: List[str] = Field(description="2-4 primary objectives of the initiative")
    implementation_bottlenecks: List[str] = Field(description="Up to 10 major, de-duplicated bottlenecks")
    stakeholder_briefing_angle: str = Field(
        description="A concise 3-sentence executive summary identifying where external data, validation, or methods support can unblock results"
    )
    tailored_outreach_memo: str = Field(
        description="A tailored, high-context briefing draft addressed to the project lead referencing specific indicators and pages"
    )


class InstitutionalAudit(Synthesis):
    """Full single-pass result: synthesis plus indicators."""

    tracked_indicators: List[ExtractedIndicator] = Field(description="Key indicators evaluated in the report")


Verification = Literal["verified", "page_corrected", "partial", "unverified", "no_quote"]


class VerifiedIndicator(ExtractedIndicator):
    verification: Verification = "no_quote"
    numbers_in_source: Optional[bool] = Field(
        None, description="True if every number in baseline/target appears in the document; None if there are no numbers"
    )


class RunMeta(BaseModel):
    filename: str = ""
    pages: int = 0
    characters: int = 0
    mode: Literal["single_pass", "map_reduce"] = "single_pass"
    chunks: int = 1
    model: str = ""
    elapsed_s: float = 0.0
    warnings: List[str] = Field(default_factory=list)


class AuditReport(BaseModel):
    synthesis: Synthesis
    indicators: List[VerifiedIndicator]
    meta: RunMeta

    @property
    def verified_count(self) -> int:
        return sum(1 for i in self.indicators if i.verification in ("verified", "page_corrected"))
