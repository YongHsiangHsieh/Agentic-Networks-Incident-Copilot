"""
Conditional routing logic for LangGraph workflow.

Determines which path to take in the workflow based on:
- Human approval status
- Diagnosis confidence
- Error conditions
- Retry limits
"""

from app.langgraph_orchestrator.state import IncidentState


def route_after_diagnosis_review(state: IncidentState) -> str:
    """
    Route after human reviews diagnosis.
    
    Options:
    - "approved" → Continue to recommendations
    - "retry" → Re-run diagnosis
    - "stop" → End workflow
    """
    if state.get("diagnosis_approved"):
        return "approved"
    
    # Check if diagnosis feedback indicates retry needed
    feedback = state.get("diagnosis_feedback", "").lower()
    if "retry" in feedback or "again" in feedback:
        return "retry"
    
    # Default to stop if not approved and no retry requested
    return "stop"


def route_after_commands_review(state: IncidentState) -> str:
    """
    Route after human reviews commands.
    
    Options:
    - "execute" → Execute commands
    - "modify" → Regenerate commands (with feedback)
    - "stop" → End workflow
    """
    if state.get("commands_approved"):
        return "execute"
    
    # Check if commands feedback indicates modification needed
    feedback = state.get("commands_feedback", "").lower()
    if "modify" in feedback or "change" in feedback or "different" in feedback:
        return "modify"
    
    # Default to stop if not approved and no modification requested
    return "stop"


def should_auto_approve_diagnosis(state: IncidentState) -> bool:
    """
    Determine if diagnosis should be auto-approved based on confidence.
    
    High-confidence diagnoses (>90%) can optionally skip human review
    for known, low-risk root causes.
    
    Note: This is conservative - in production, you may want all
    diagnoses to require human review initially.
    """
    confidence = state.get("diagnosis_confidence", 0.0)
    root_cause = state.get("diagnosis", {}).get("root_cause", "unknown")
    
    # Only auto-approve very high confidence on known causes
    if confidence > 0.90 and root_cause in ["congestion", "config_change"]:
        # Even then, require explicit opt-in
        return state.get("auto_approve_diagnosis", False)
    
    return False


def should_retry_diagnosis(state: IncidentState) -> bool:
    """
    Determine if diagnosis should be retried after failure.
    
    Returns True if:
    - Diagnosis failed (no result or very low confidence)
    - Retry count < max retries (3)
    """
    retry_count = state.get("retry_count", 0)
    if retry_count >= 3:
        return False
    
    diagnosis = state.get("diagnosis")
    if not diagnosis:
        return True
    
    confidence = state.get("diagnosis_confidence", 0.0)
    if confidence < 0.3:  # Very low confidence
        return True
    
    return False


def route_after_execution(state: IncidentState) -> str:
    """
    Route after command execution.
    
    Options:
    - "rca" → Generate RCA report
    - "retry" → Retry execution (if failed)
    - "stop" → End workflow (if fatal error)
    """
    execution_status = state.get("execution_status", "unknown")
    
    if execution_status == "success":
        return "rca"
    
    if execution_status == "partial":
        # Partial success → still generate RCA
        return "rca"
    
    if execution_status == "failed":
        retry_count = state.get("execution_retry_count", 0)
        if retry_count < 2:
            state["execution_retry_count"] = retry_count + 1
            return "retry"
        else:
            # Max retries exceeded → stop
            return "stop"
    
    # Default: continue to RCA
    return "rca"


def get_workflow_priority(state: IncidentState) -> str:
    """
    Get workflow priority based on incident severity.
    
    Used to determine SLA and notification urgency.
    """
    priority = state.get("priority", "medium")
    
    # Can escalate based on metrics
    incident_data = state.get("incident_data", {})
    latency_current = incident_data.get("latency_current", 0)
    loss_current = incident_data.get("loss_current", 0)
    
    # Critical thresholds
    if latency_current > 500 or loss_current > 10:
        return "critical"
    
    if latency_current > 200 or loss_current > 5:
        return "high"
    
    return priority

