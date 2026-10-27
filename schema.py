from typing import List, Optional
from pydantic import BaseModel, Field

class IndicatorTarget(BaseModel):
    indicator_name: str = Field(description="Name or metric of the tracked indicator")
    baseline_value: Optional[str] = Field(None, description="Stated baseline or starting benchmark")
    target_value: Optional[str] = Field(None, description="Target goal or outcome benchmark")
    status_or_evidence_gap: str = Field(description="Observed data gap, delay, or measurement challenge")

class InstitutionalAudit(BaseModel):
    institution_name: str = Field(description="Executing agency or institution (e.g., Asian Development Bank, World Bank)")
    project_title: str = Field(description="Title of the project, program, or policy initiative")
    sector: str = Field(description="Core sector (e.g., Energy Transition, Public Governance, Digital Infrastructure)")
    core_objectives: List[str] = Field(description="2-3 primary objectives of the initiative")
    tracked_indicators: List[IndicatorTarget] = Field(description="Key indicators evaluated in the report")
    implementation_bottlenecks: List[str] = Field(description="Major operational, monitoring, or institutional bottlenecks noted")
    stakeholder_briefing_angle: str = Field(
        description="A concise 3-sentence executive summary identifying where external data, validation, or methods support can unblock results"
    )
    tailored_outreach_memo: str = Field(
        description="A tailored, high-context briefing draft addressed to the project lead referencing specific page metrics or indicators"
    )