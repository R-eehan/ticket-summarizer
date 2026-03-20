"""
Pydantic schemas for structured LLM outputs.

These schemas are used with native structured output APIs:
- Azure OpenAI: response_format with json_schema
- Gemini: response_mime_type="application/json" with response_schema

All fields are required (no defaults) for compatibility with both providers.
Optional fields accept null values but must be explicitly provided by the LLM.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# ============================================================================
# SYNTHESIS SCHEMA
# ============================================================================

class TicketSynthesis(BaseModel):
    issue_reported: str = Field(
        description="One-liner describing what the customer initially reported or the actual issue identified"
    )
    root_cause: str = Field(
        description="One-liner describing the underlying technical cause of the issue"
    )
    summary: str = Field(
        description="3-4 line paragraph capturing the ticket essence, key troubleshooting steps, turning points, and how the solution was reached"
    )
    resolution: str = Field(
        description="One-liner stating how the issue was actually resolved"
    )


# ============================================================================
# CATEGORIZATION SCHEMA
# ============================================================================

class PODEnum(str, Enum):
    WFE = "WFE"
    Guidance = "Guidance"
    CMM = "CMM"
    Hub = "Hub"
    Analytics = "Analytics"
    Insights = "Insights"
    Capture = "Capture"
    Mirror = "Mirror"
    Desktop = "Desktop"
    Mobile = "Mobile"
    Labs = "Labs"
    PlatformServices = "Platform Services"
    UIPlatform = "UI Platform"


class ConfidenceEnum(str, Enum):
    confident = "confident"
    not_confident = "not confident"


class TicketCategorization(BaseModel):
    primary_pod: str = Field(
        description="The primary POD: one of WFE, Guidance, CMM, Hub, Analytics, Insights, Capture, Mirror, Desktop, Mobile, Labs, Platform Services, UI Platform"
    )
    reasoning: str = Field(
        description="2-3 sentences explaining why this POD was chosen based on the synthesis"
    )
    confidence: str = Field(
        description="Either 'confident' or 'not confident'"
    )
    confidence_reason: str = Field(
        description="Single sentence explaining why this confidence level was assigned"
    )
    alternative_pods: List[str] = Field(
        description="Other PODs this could belong to, or empty list if no alternatives"
    )
    alternative_reasoning: Optional[str] = Field(
        description="1-2 sentences explaining why alternatives were considered, or null if no alternatives"
    )


# ============================================================================
# DIAGNOSTICS ANALYSIS SCHEMA
# ============================================================================

class DiagnosticsUsage(BaseModel):
    llm_assessment: str = Field(
        description="Assessment of whether Diagnostics was used: 'yes', 'no', or 'unknown'"
    )
    confidence: str = Field(
        description="Either 'confident' or 'not confident'"
    )
    reasoning: str = Field(
        description="Explanation based on synthesis evidence"
    )


class DiagnosticsHelp(BaseModel):
    triage_assessment: str = Field(
        description="Could Diagnostics help identify the issue: 'yes', 'no', or 'maybe'"
    )
    triage_reasoning: str = Field(
        description="Why Diagnostics could/couldn't help IDENTIFY the issue"
    )
    triage_gap_area: Optional[str] = Field(
        description="Gap area when triage_assessment is 'no' or 'maybe', null when 'yes'"
    )
    triage_gap_description: Optional[str] = Field(
        description="Description only required if triage_gap_area is 'other_triage_gap', otherwise null"
    )
    fix_assessment: str = Field(
        description="Could Diagnostics recommend a fix: 'yes', 'no', or 'maybe'"
    )
    fix_reasoning: str = Field(
        description="Why Diagnostics could/couldn't RECOMMEND a self-service fix"
    )
    fix_gap_area: Optional[str] = Field(
        description="Gap area when fix_assessment is 'no' or 'maybe', null when 'yes'"
    )
    fix_gap_description: Optional[str] = Field(
        description="Description only required if fix_gap_area is 'other_fix_gap', otherwise null"
    )
    confidence: str = Field(
        description="Either 'confident' or 'not confident'"
    )
    diagnostics_capability_matched: List[str] = Field(
        description="List of Diagnostics capabilities that match this ticket, or empty list"
    )
    limitation_notes: Optional[str] = Field(
        description="Explanation of specific limitations that apply, or null"
    )


class DiagnosticsMetadata(BaseModel):
    ticket_type: str = Field(
        description="One of: 'troubleshooting', 'feature_request', 'technical_request', 'unclear'"
    )


class DiagnosticsAnalysis(BaseModel):
    was_diagnostics_used: DiagnosticsUsage
    could_diagnostics_help: DiagnosticsHelp
    metadata: DiagnosticsMetadata
