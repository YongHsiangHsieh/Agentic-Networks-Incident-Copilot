"""
Simplified data models for RCA Generator.

Focus: Clean, minimal models for incident data and RCA generation.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class IncidentMetrics(BaseModel):
    """Time series metrics captured during an incident."""
    latency_ms: List[float] = Field(
        description="Latency measurements over time (milliseconds)"
    )
    loss_pct: List[float] = Field(
        description="Packet loss percentages over time"
    )
    util_pct: Dict[str, List[float]] = Field(
        description="Utilization per network segment over time",
        default_factory=dict
    )


class IncidentData(BaseModel):
    """Complete incident data package for RCA generation."""
    
    # Basic info
    incident_id: str = Field(description="Unique incident identifier")
    timestamp_start: str = Field(description="When incident started (ISO 8601)")
    timestamp_end: str = Field(description="When incident was resolved (ISO 8601)")
    
    # Network context
    hot_path: str = Field(
        description="Network path affected (e.g., 'RouterA->RouterB->RouterC')"
    )
    
    # Metrics
    metrics: IncidentMetrics = Field(description="Time series metrics")
    
    # Actions and resolution
    actions_taken: List[str] = Field(
        description="Chronological list of actions taken during incident",
        default_factory=list
    )
    resolution_summary: str = Field(
        description="Brief summary of how incident was resolved"
    )
    
    # Optional context
    engineer_notes: Optional[str] = Field(
        default=None,
        description="Additional notes from engineer (optional)"
    )
    recent_changes: Optional[bool] = Field(
        default=False,
        description="Were there recent config/deployment changes?"
    )
    change_details: Optional[str] = Field(
        default=None,
        description="Details about recent changes if any"
    )


class RCAOutput(BaseModel):
    """Generated RCA report output."""
    incident_id: str
    rca_markdown: str = Field(description="RCA report in Markdown format")
    generation_time_sec: float = Field(description="Time taken to generate")
    root_cause: str = Field(description="Identified root cause")
    confidence: float = Field(description="Confidence in diagnosis (0-1)")
