"""
Pydantic data models for the Incident Playbook Picker system.
"""

from pydantic import BaseModel
from typing import List, Dict, Optional, Any


class ChangeEvent(BaseModel):
    """Represents a configuration or deployment change event."""
    ts: str  # ISO 8601 timestamp
    type: str  # e.g., "config_change", "deployment"
    scope: str  # e.g., "router-A", "segment-XY"


class Policy(BaseModel):
    """Operational policy constraints."""
    latency_target_ms: int
    min_path_redundancy: int
    max_burst_cost_per_hr_eur: float


class Prices(BaseModel):
    """Pricing information for cost calculations."""
    burst_capacity_per_1Gbps_hr: float


class MetricsWindow(BaseModel):
    """Time-series metrics over an incident window."""
    latency_ms: List[float]
    loss_pct: List[float]
    util_pct: Dict[str, List[float]]  # utilization per segment


class IncidentBundle(BaseModel):
    """Complete incident data package for analysis."""
    incident_id: str
    window: Dict[str, Any]  # e.g., {"start_ts": ..., "end_ts": ...}
    hot_path: str  # e.g., "A->B->C"
    metrics: MetricsWindow
    changes: List[ChangeEvent]
    policy: Policy
    prices_eur: Prices


class CandidateOption(BaseModel):
    """A potential remediation option with predictions."""
    id: str
    kind: str
    eta_minutes: int
    pred_latency_ms: float
    pred_loss_pct: float
    risk: str
    euro_delta: float
    policy_verdict: Dict[str, Any]
    explanation: Optional[str] = None


class IncidentState(BaseModel):
    """State object passed through the LangGraph workflow."""
    incident_id: str
    bundle: IncidentBundle
    signals: Optional[Dict[str, Any]] = None
    change_context: Optional[Dict[str, Any]] = None
    hypothesis: Optional[Dict[str, Any]] = None
    candidates: Optional[List[CandidateOption]] = None
    policy_verdicts: Optional[List[Dict[str, Any]]] = None
    recommendation: Optional[CandidateOption] = None
    plan: Optional[Dict[str, Any]] = None
    artifacts: Optional[Dict[str, str]] = None
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

