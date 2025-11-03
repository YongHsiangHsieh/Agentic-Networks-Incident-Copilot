"""
State model for LangGraph-based incident response workflow.

The state persists across the entire workflow and includes:
- Incident data and context
- Diagnosis results
- Recommendations
- Generated commands
- Execution results
- RCA report
- Approval status
- Full audit trail
"""

from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime


class IncidentState(TypedDict, total=False):
    """
    Complete state for incident response workflow.
    
    This state persists across interruptions and can be resumed at any checkpoint.
    All fields are optional to allow partial state updates.
    """
    
    # ===== INPUT =====
    incident_id: str  # Unique incident identifier
    incident_data: Dict[str, Any]  # Raw incident data (metrics, paths, etc.)
    
    # ===== DIAGNOSIS =====
    diagnosis: Optional[Dict[str, Any]]  # Root cause diagnosis result
    diagnosis_confidence: Optional[float]  # Diagnosis confidence (0-1)
    diagnosis_approved: bool  # Human approval for diagnosis
    diagnosis_feedback: Optional[str]  # Human feedback on diagnosis
    
    # ===== RECOMMENDATIONS =====
    recommendations: Optional[List[Dict[str, Any]]]  # Ranked playbook options
    selected_playbook_id: Optional[str]  # Playbook selected by human
    recommendation_reasoning: Optional[str]  # Why this playbook was recommended
    
    # ===== COMMANDS =====
    commands: Optional[Dict[str, Any]]  # Generated commands for execution
    commands_approved: bool  # Human approval for command execution
    commands_feedback: Optional[str]  # Human feedback on commands
    commands_modified: Optional[Dict[str, Any]]  # Modified commands (if any)
    
    # ===== EXECUTION =====
    execution_result: Optional[Dict[str, Any]]  # Result of command execution
    execution_status: Optional[str]  # "success", "partial", "failed"
    execution_timestamp: Optional[str]  # When commands were executed
    
    # ===== RCA =====
    rca_report: Optional[str]  # Generated RCA report (markdown)
    rca_generated_at: Optional[str]  # When RCA was generated
    
    # ===== WORKFLOW STATE =====
    current_step: Optional[str]  # Current node in workflow
    workflow_status: Optional[str]  # "running", "paused", "completed", "failed"
    retry_count: int  # Number of retries for current step
    
    # ===== APPROVALS & AUDIT =====
    approvals: List[Dict[str, Any]]  # List of all human approvals
    # Each approval: {
    #   "step": "diagnosis" | "commands",
    #   "approved": bool,
    #   "approved_by": "engineer@company.com",
    #   "timestamp": "2024-11-02T14:30:00Z",
    #   "feedback": "Looks good, proceed"
    # }
    
    history: List[Dict[str, Any]]  # Full workflow history
    # Each history entry: {
    #   "step": "diagnose" | "recommend" | "generate_commands" | etc.,
    #   "timestamp": "2024-11-02T14:30:00Z",
    #   "duration_ms": 2345,
    #   "result": {...}
    # }
    
    errors: List[Dict[str, Any]]  # Error log
    # Each error: {
    #   "step": "diagnose",
    #   "error": "AWS Bedrock timeout",
    #   "timestamp": "2024-11-02T14:30:00Z",
    #   "retry_attempt": 1
    # }
    
    # ===== METADATA =====
    created_at: Optional[str]  # Workflow creation time
    updated_at: Optional[str]  # Last update time
    created_by: Optional[str]  # Engineer who initiated workflow
    priority: Optional[str]  # "low", "medium", "high", "critical"
    tags: Optional[List[str]]  # Tags for categorization


def create_initial_state(
    incident_id: str,
    incident_data: Dict[str, Any],
    created_by: Optional[str] = None,
    priority: str = "medium"
) -> IncidentState:
    """
    Create initial state for a new incident workflow.
    
    Args:
        incident_id: Unique incident identifier
        incident_data: Incident metrics and context
        created_by: Engineer who initiated the workflow
        priority: Incident priority level
    
    Returns:
        Initial IncidentState with timestamp and defaults
    """
    now = datetime.utcnow().isoformat() + "Z"
    
    return IncidentState(
        incident_id=incident_id,
        incident_data=incident_data,
        
        # Initialize approval flags
        diagnosis_approved=False,
        commands_approved=False,
        
        # Initialize collections
        approvals=[],
        history=[],
        errors=[],
        
        # Workflow state
        current_step="start",
        workflow_status="running",
        retry_count=0,
        
        # Metadata
        created_at=now,
        updated_at=now,
        created_by=created_by,
        priority=priority,
        tags=[]
    )


def update_state_timestamp(state: IncidentState) -> IncidentState:
    """Update the updated_at timestamp in state."""
    state["updated_at"] = datetime.utcnow().isoformat() + "Z"
    return state


def add_history_entry(
    state: IncidentState,
    step: str,
    duration_ms: Optional[int] = None,
    result: Optional[Any] = None
) -> IncidentState:
    """Add an entry to the workflow history."""
    entry = {
        "step": step,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    if duration_ms is not None:
        entry["duration_ms"] = duration_ms
    
    if result is not None:
        entry["result"] = result
    
    if "history" not in state:
        state["history"] = []
    
    state["history"].append(entry)
    return update_state_timestamp(state)


def add_approval(
    state: IncidentState,
    step: str,
    approved: bool,
    approved_by: Optional[str] = None,
    feedback: Optional[str] = None
) -> IncidentState:
    """Add a human approval to the audit trail."""
    approval = {
        "step": step,
        "approved": approved,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    if approved_by:
        approval["approved_by"] = approved_by
    
    if feedback:
        approval["feedback"] = feedback
    
    if "approvals" not in state:
        state["approvals"] = []
    
    state["approvals"].append(approval)
    return update_state_timestamp(state)


def add_error(
    state: IncidentState,
    step: str,
    error: str,
    retry_attempt: Optional[int] = None
) -> IncidentState:
    """Add an error to the error log."""
    error_entry = {
        "step": step,
        "error": error,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    if retry_attempt is not None:
        error_entry["retry_attempt"] = retry_attempt
    
    if "errors" not in state:
        state["errors"] = []
    
    state["errors"].append(error_entry)
    return update_state_timestamp(state)

