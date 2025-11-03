"""
Production API endpoints for LangGraph workflow management.

Provides REST API for:
- Starting new incident workflows
- Checking workflow status
- Approving/rejecting at checkpoints
- Viewing history and audit trail
- Resuming paused workflows

These endpoints solve real problems:
- Engineers can automate incident response
- Integrate with monitoring/alerting systems
- Build custom UIs on top of the workflow
- Programmatic access for scripts/tools
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.langgraph_orchestrator.graph import get_workflow_instance
from app.langgraph_orchestrator.state import create_initial_state

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


# ===== REQUEST/RESPONSE MODELS =====

class StartWorkflowRequest(BaseModel):
    """Request to start a new incident workflow."""
    incident_id: str = Field(..., description="Unique incident identifier")
    hot_path: str = Field(..., description="Affected network path")
    latency_current: float = Field(..., description="Current latency in ms")
    latency_baseline: Optional[float] = Field(None, description="Baseline latency in ms")
    loss_current: float = Field(..., description="Current packet loss %")
    loss_baseline: Optional[float] = Field(None, description="Baseline packet loss %")
    utilization: Optional[Dict[str, float]] = Field(default_factory=dict, description="Utilization by segment")
    recent_changes: Optional[List[str]] = Field(default_factory=list, description="Recent configuration changes")
    priority: Optional[str] = Field("medium", description="Incident priority: low/medium/high/critical")
    created_by: Optional[str] = Field(None, description="Engineer email who started workflow")


class ApprovalRequest(BaseModel):
    """Request to approve or reject at a checkpoint."""
    approved: bool = Field(..., description="True to approve, False to reject")
    feedback: Optional[str] = Field(None, description="Engineer's feedback/comments")
    approved_by: Optional[str] = Field(None, description="Engineer email who approved")


class WorkflowStatusResponse(BaseModel):
    """Response with current workflow status."""
    incident_id: str
    current_step: Optional[str]
    workflow_status: Optional[str]
    diagnosis: Optional[Dict]
    recommendations: Optional[List[Dict]]
    commands: Optional[Dict]
    execution_result: Optional[Dict]
    approvals_pending: List[str]
    history_count: int
    approvals_count: int
    errors_count: int
    created_at: Optional[str]
    updated_at: Optional[str]


# ===== ENDPOINTS =====

@router.post("/start", response_model=Dict)
async def start_workflow(request: StartWorkflowRequest):
    """
    Start a new incident response workflow.
    
    This initiates the workflow and runs until the first human approval gate.
    Engineers can then review the diagnosis before proceeding.
    
    Real-world use case:
    - Called by monitoring system when alert fires
    - Called by engineer via CLI/UI
    - Integrated into incident management platform
    """
    try:
        # Create initial state
        initial_state = create_initial_state(
            incident_id=request.incident_id,
            incident_data={
                "hot_path": request.hot_path,
                "latency_current": request.latency_current,
                "latency_baseline": request.latency_baseline or request.latency_current * 0.5,
                "loss_current": request.loss_current,
                "loss_baseline": request.loss_baseline or 0.1,
                "utilization": request.utilization or {},
                "recent_changes": request.recent_changes or [],
                "priority": request.priority
            },
            created_by=request.created_by,
            priority=request.priority or "medium"
        )
        
        # Get workflow
        app = get_workflow_instance()
        
        # Start workflow (runs until first interrupt)
        result = app.invoke(
            initial_state,
            config={"configurable": {"thread_id": request.incident_id}}
        )
        
        # Build response
        return {
            "status": "success",
            "message": f"Workflow started for incident {request.incident_id}",
            "incident_id": request.incident_id,
            "current_step": result.get("current_step"),
            "workflow_status": result.get("workflow_status"),
            "diagnosis": result.get("diagnosis"),
            "next_action": "Review diagnosis and call /workflows/{incident_id}/approve-diagnosis"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start workflow: {str(e)}"
        )


@router.get("/{incident_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(incident_id: str):
    """
    Get current status of a workflow.
    
    Shows:
    - Current workflow step
    - Diagnosis results
    - Recommendations
    - Pending approvals
    - History and audit trail
    
    Real-world use case:
    - Check workflow progress
    - Display in dashboard/UI
    - Monitor for SLA compliance
    """
    try:
        app = get_workflow_instance()
        
        # Get current state
        state = app.get_state(config={"configurable": {"thread_id": incident_id}})
        
        if not state or not state.values:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow not found for incident {incident_id}"
            )
        
        values = state.values
        
        # Determine pending approvals
        pending = []
        if not values.get("diagnosis_approved"):
            pending.append("diagnosis")
        if values.get("diagnosis_approved") and not values.get("commands_approved"):
            pending.append("commands")
        
        return WorkflowStatusResponse(
            incident_id=incident_id,
            current_step=values.get("current_step"),
            workflow_status=values.get("workflow_status"),
            diagnosis=values.get("diagnosis"),
            recommendations=values.get("recommendations"),
            commands=values.get("commands"),
            execution_result=values.get("execution_result"),
            approvals_pending=pending,
            history_count=len(values.get("history", [])),
            approvals_count=len(values.get("approvals", [])),
            errors_count=len(values.get("errors", [])),
            created_at=values.get("created_at"),
            updated_at=values.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get workflow status: {str(e)}"
        )


@router.post("/{incident_id}/approve-diagnosis")
async def approve_diagnosis(
    incident_id: str,
    approval: ApprovalRequest = Body(...)
):
    """
    Approve or reject diagnosis and resume workflow.
    
    If approved: Continues to recommendations and command generation
    If rejected: Can re-run diagnosis or stop workflow
    
    Real-world use case:
    - Engineer reviews AI diagnosis
    - Approves if correct, rejects if wrong
    - Provides feedback for audit trail
    """
    try:
        app = get_workflow_instance()
        config = {"configurable": {"thread_id": incident_id}}
        
        # Update state with approval
        app.update_state(
            config=config,
            values={
                "diagnosis_approved": approval.approved,
                "diagnosis_feedback": approval.feedback,
                "approvals": [{
                    "step": "diagnosis",
                    "approved": approval.approved,
                    "approved_by": approval.approved_by,
                    "feedback": approval.feedback,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }]
            }
        )
        
        # Resume workflow if approved
        if approval.approved:
            result = app.invoke(None, config=config)
            
            return {
                "status": "success",
                "message": "Diagnosis approved, workflow resumed",
                "incident_id": incident_id,
                "current_step": result.get("current_step"),
                "recommendations": result.get("recommendations"),
                "commands": result.get("commands"),
                "next_action": "Review commands and call /workflows/{incident_id}/approve-commands"
            }
        else:
            return {
                "status": "success",
                "message": "Diagnosis rejected, workflow paused",
                "incident_id": incident_id,
                "next_action": "Workflow stopped. Start new workflow if needed."
            }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process approval: {str(e)}"
        )


@router.post("/{incident_id}/approve-commands")
async def approve_commands(
    incident_id: str,
    approval: ApprovalRequest = Body(...)
):
    """
    Approve or reject commands and resume workflow.
    
    If approved: Executes commands and generates RCA
    If rejected: Can modify commands or stop workflow
    
    Real-world use case:
    - Engineer reviews generated commands for safety
    - Approves if safe, rejects if risky
    - Final checkpoint before production changes
    """
    try:
        app = get_workflow_instance()
        config = {"configurable": {"thread_id": incident_id}}
        
        # Get current state to append approval
        state = app.get_state(config=config)
        current_approvals = state.values.get("approvals", [])
        
        # Add new approval
        new_approval = {
            "step": "commands",
            "approved": approval.approved,
            "approved_by": approval.approved_by,
            "feedback": approval.feedback,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Update state
        app.update_state(
            config=config,
            values={
                "commands_approved": approval.approved,
                "commands_feedback": approval.feedback,
                "approvals": current_approvals + [new_approval]
            }
        )
        
        # Resume workflow if approved
        if approval.approved:
            result = app.invoke(None, config=config)
            
            return {
                "status": "success",
                "message": "Commands approved, workflow completed",
                "incident_id": incident_id,
                "execution_result": result.get("execution_result"),
                "rca_report": result.get("rca_report"),
                "workflow_complete": True
            }
        else:
            return {
                "status": "success",
                "message": "Commands rejected, workflow paused",
                "incident_id": incident_id,
                "next_action": "Modify commands or stop workflow"
            }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process approval: {str(e)}"
        )


@router.get("/{incident_id}/history")
async def get_workflow_history(incident_id: str):
    """
    Get complete workflow history and audit trail.
    
    Returns:
    - All workflow steps executed
    - All approvals with timestamps
    - All errors encountered
    - Complete audit trail
    
    Real-world use case:
    - Compliance audits
    - Post-incident review
    - Debugging workflow issues
    - Learning from incidents
    """
    try:
        app = get_workflow_instance()
        state = app.get_state(config={"configurable": {"thread_id": incident_id}})
        
        if not state or not state.values:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow not found for incident {incident_id}"
            )
        
        values = state.values
        
        return {
            "incident_id": incident_id,
            "created_at": values.get("created_at"),
            "updated_at": values.get("updated_at"),
            "created_by": values.get("created_by"),
            "priority": values.get("priority"),
            "history": values.get("history", []),
            "approvals": values.get("approvals", []),
            "errors": values.get("errors", []),
            "diagnosis": values.get("diagnosis"),
            "recommendations": values.get("recommendations"),
            "execution_result": values.get("execution_result"),
            "rca_report": values.get("rca_report")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get workflow history: {str(e)}"
        )


@router.post("/{incident_id}/select-playbook")
async def select_playbook(
    incident_id: str,
    playbook_id: str = Body(..., embed=True)
):
    """
    Manually select a specific playbook (override AI recommendation).
    
    Real-world use case:
    - Engineer wants different playbook than AI recommended
    - Override based on operational knowledge
    - Select alternative if top choice unavailable
    """
    try:
        app = get_workflow_instance()
        config = {"configurable": {"thread_id": incident_id}}
        
        # Update state with selected playbook
        app.update_state(
            config=config,
            values={"selected_playbook_id": playbook_id}
        )
        
        return {
            "status": "success",
            "message": f"Playbook {playbook_id} selected",
            "incident_id": incident_id,
            "selected_playbook": playbook_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to select playbook: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "workflow-api",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

