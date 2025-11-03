"""
Network Incident Copilot API - Complete AI-powered incident response system.

Provides endpoints for diagnosis, recommendations, command generation, and RCA.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import time

from app.models import IncidentData, RCAOutput
from app.api.workflow_endpoints import router as workflow_router

app = FastAPI(
    title="Network Incident Copilot",
    description="AI-powered copilot for network incident response: diagnosis, recommendations, commands, and RCA",
    version="4.0.0"
)

# Include LangGraph workflow management endpoints
app.include_router(workflow_router)


@app.get("/")
def root():
    """Root endpoint with API info."""
    return {
        "service": "Network Incident Copilot",
        "version": "4.0.0",
        "status": "running",
        "description": "Production-ready AI copilot with LangGraph workflows, human-in-the-loop, and full audit trail",
        "features": [
            "Human-in-the-loop approval gates",
            "State persistence and resumability",
            "Hybrid AI + rule-based recommendations",
            "Full audit trail for compliance",
            "Error recovery with automatic retries"
        ],
        "endpoints": {
            "legacy": {
                "health": "/health",
                "diagnose": "/diagnose",
                "recommend": "/recommend",
                "commands": "/commands",
                "generate_rca": "/generate_rca",
                "full_workflow": "/full_workflow"
            },
            "workflows (production)": {
                "start": "POST /api/workflows/start",
                "status": "GET /api/workflows/{incident_id}/status",
                "approve_diagnosis": "POST /api/workflows/{incident_id}/approve-diagnosis",
                "approve_commands": "POST /api/workflows/{incident_id}/approve-commands",
                "history": "GET /api/workflows/{incident_id}/history",
                "select_playbook": "POST /api/workflows/{incident_id}/select-playbook",
                "health": "GET /api/workflows/health"
            }
        },
        "interfaces": [
            "REST API (this) - Production workflows",
            "MCP Server (Claude Desktop) - Human-in-the-loop",
            "LangGraph Orchestrator - State management"
        ],
        "docs": "/docs"
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Request/Response models for new endpoints
class DiagnoseRequest(BaseModel):
    hot_path: str = Field(..., description="Affected network path (e.g., 'RouterB-RouterC')")
    latency_current: float = Field(..., description="Current latency in milliseconds")
    latency_baseline: float = Field(default=45.0, description="Baseline latency")
    loss_current: float = Field(..., description="Current packet loss percentage")
    loss_baseline: float = Field(default=0.05, description="Baseline packet loss")
    utilization: Dict[str, float] = Field(default={}, description="Utilization by segment")
    recent_changes: List[str] = Field(default=[], description="Recent changes")


class RecommendRequest(BaseModel):
    root_cause: str = Field(..., description="Identified root cause")
    confidence: float = Field(..., description="Diagnosis confidence 0.0-1.0")
    hot_path: str
    latency_current: Optional[float] = None
    loss_current: Optional[float] = None
    utilization: Optional[Dict[str, float]] = None


class CommandRequest(BaseModel):
    playbook_id: str = Field(..., description="Playbook ID (e.g., 'qos_traffic_shaping')")
    hot_path: str
    latency_current: Optional[float] = 125
    loss_current: Optional[float] = 2.0
    include_verification: bool = True
    include_rollback: bool = True


@app.post("/diagnose")
async def diagnose_incident(request: DiagnoseRequest):
    """
    Diagnose a network incident and identify root cause.
    
    Returns diagnosis with confidence level, evidence, and severity.
    Use this as the first step when investigating any network issue.
    """
    try:
        from app.copilot import get_copilot
        
        copilot = get_copilot()
        incident_data = {
            "hot_path": request.hot_path,
            "latency_current": request.latency_current,
            "latency_baseline": request.latency_baseline,
            "loss_current": request.loss_current,
            "loss_baseline": request.loss_baseline,
            "utilization": request.utilization,
            "actions_taken": request.recent_changes,
            "metrics": {
                "latency_ms": [request.latency_baseline, request.latency_current],
                "loss_pct": [request.loss_baseline, request.loss_current],
                "util_pct": request.utilization,
            }
        }
        
        result = copilot.diagnose(incident_data)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diagnosis failed: {str(e)}")


@app.post("/recommend")
async def recommend_actions(request: RecommendRequest):
    """
    Get ranked remediation recommendations based on diagnosis.
    
    Returns top 3 options with risk analysis, impact estimates, and reasoning.
    """
    try:
        from app.copilot import get_copilot
        
        copilot = get_copilot()
        diagnosis = {
            "root_cause": request.root_cause,
            "confidence": request.confidence,
        }
        context = {
            "hot_path": request.hot_path,
            "latency_current": request.latency_current,
            "loss_current": request.loss_current,
            "utilization": request.utilization or {},
        }
        
        result = copilot.recommend(diagnosis, context, top_n=3)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")


@app.post("/commands")
async def generate_commands(request: CommandRequest):
    """
    Generate CLI commands for a specific remediation playbook.
    
    Returns personalized commands with verification steps, rollback, and warnings.
    """
    try:
        from app.copilot import get_copilot
        
        copilot = get_copilot()
        context = {
            "hot_path": request.hot_path,
            "latency_current": request.latency_current,
            "loss_current": request.loss_current,
            "latency_baseline": 45,
            "loss_baseline": 0.05,
        }
        
        result = copilot.generate_commands(
            playbook_id=request.playbook_id,
            incident_context=context,
            include_verification=request.include_verification,
            include_rollback=request.include_rollback
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Command generation failed: {str(e)}")


@app.post("/full_workflow")
async def full_workflow(request: DiagnoseRequest):
    """
    Complete copilot workflow: Diagnose → Recommend → Ready to Execute
    
    One-stop endpoint that provides complete analysis and next steps.
    """
    try:
        from app.copilot import get_copilot
        
        copilot = get_copilot()
        incident_data = {
            "hot_path": request.hot_path,
            "latency_current": request.latency_current,
            "latency_baseline": request.latency_baseline,
            "loss_current": request.loss_current,
            "loss_baseline": request.loss_baseline,
            "utilization": request.utilization,
            "metrics": {
                "latency_ms": [request.latency_baseline, request.latency_current],
                "loss_pct": [request.loss_baseline, request.loss_current],
                "util_pct": request.utilization,
            }
        }
        
        result = copilot.full_workflow(incident_data)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")


@app.post("/generate_rca", response_model=RCAOutput)
async def generate_rca(incident: IncidentData):
    """
    Generate Root Cause Analysis report from incident data.
    
    This endpoint takes post-incident data and generates a comprehensive
    RCA report that engineers can review and submit.
    
    **Low Risk**: Called AFTER incident is resolved, for documentation only.
    """
    try:
        start_time = time.time()
        
        # Import here to avoid circular dependencies
        from app.agents.rca_generator import RCAGenerator
        
        # Generate RCA
        generator = RCAGenerator()
        rca_report = generator.generate(incident)
        
        generation_time = time.time() - start_time
        
        return RCAOutput(
            incident_id=incident.incident_id,
            rca_markdown=rca_report['markdown'],
            generation_time_sec=generation_time,
            root_cause=rca_report['root_cause'],
            confidence=rca_report['confidence']
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate RCA: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
