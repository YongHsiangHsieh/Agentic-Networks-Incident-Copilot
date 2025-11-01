"""
FastAPI application for Incident Playbook Picker.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import time

from app.models import IncidentBundle, IncidentState
from app.graph import build_graph, run_graph_until, run_graph_from

# Create FastAPI app
app = FastAPI(
    title="Incident Playbook Picker",
    description="Automated incident diagnosis and remediation recommendation system",
    version="1.0.0"
)

# Build and cache the graph
graph = build_graph(include_justification=False)

# In-memory state store (for demo purposes)
# In production, this would be a proper database
state_store = {}


class ApplyOptionRequest(BaseModel):
    """Request model for applying a remediation option."""
    incident_id: str
    option_id: str


@app.get("/")
def read_root():
    """Root endpoint with API information."""
    return {
        "name": "Incident Playbook Picker",
        "version": "1.0.0",
        "endpoints": [
            "/diagnose_issue",
            "/apply_option"
        ]
    }


@app.post("/diagnose_issue")
def diagnose_issue(bundle: IncidentBundle):
    """
    Diagnose an incident and return ranked remediation options.
    
    This endpoint runs the analysis workflow up to the policy gate,
    providing hypothesis, candidates, and policy verdicts without
    executing any remediation.
    
    Args:
        bundle: Complete incident data package
        
    Returns:
        dict with hypothesis, candidates, and policy_verdicts
    """
    try:
        start_time = time.time()
        
        # Create initial state
        initial_state = IncidentState(
            incident_id=bundle.incident_id,
            bundle=bundle
        )
        
        # Run graph until policy_gate
        final_state = run_graph_until(
            graph=graph,
            state=initial_state,
            stop_at="policy_gate"
        )
        
        # Store state for potential apply_option call
        state_store[bundle.incident_id] = final_state
        
        elapsed_time = time.time() - start_time
        
        # Check for errors
        if final_state.error:
            return JSONResponse(
                status_code=500,
                content={
                    "error": final_state.error,
                    "elapsed_time_sec": elapsed_time
                }
            )
        
        # Return diagnosis results
        return {
            "hypothesis": final_state.hypothesis,
            "candidates": [c.model_dump() for c in final_state.candidates] if final_state.candidates else [],
            "policy_verdicts": final_state.policy_verdicts,
            "recommendation": final_state.recommendation.model_dump() if final_state.recommendation else None,
            "elapsed_time_sec": round(elapsed_time, 3)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing incident: {str(e)}")


@app.post("/apply_option")
def apply_option(request: ApplyOptionRequest):
    """
    Apply a selected remediation option and generate artifacts.
    
    This endpoint continues the workflow from plan synthesis through
    artifact generation for a previously diagnosed incident.
    
    Args:
        request: Incident ID and selected option ID
        
    Returns:
        dict with plan and artifact paths
    """
    try:
        start_time = time.time()
        
        incident_id = request.incident_id
        option_id = request.option_id
        
        # Retrieve state from store
        if incident_id not in state_store:
            raise HTTPException(
                status_code=404,
                detail=f"Incident {incident_id} not found. Please run /diagnose_issue first."
            )
        
        state = state_store[incident_id]
        
        # Find the selected option in candidates
        selected_candidate = None
        if state.candidates:
            for candidate in state.candidates:
                if candidate.id == option_id:
                    selected_candidate = candidate
                    break
        
        if not selected_candidate:
            raise HTTPException(
                status_code=400,
                detail=f"Option {option_id} not found in candidates for incident {incident_id}"
            )
        
        # Set the selected candidate as the recommendation
        state.recommendation = selected_candidate
        
        # Run from synthesize_plan onwards
        final_state = run_graph_from(
            graph=graph,
            state=state,
            start_from="synthesize_plan"
        )
        
        # Update stored state
        state_store[incident_id] = final_state
        
        elapsed_time = time.time() - start_time
        
        # Check for errors
        if final_state.error:
            return JSONResponse(
                status_code=500,
                content={
                    "error": final_state.error,
                    "elapsed_time_sec": elapsed_time
                }
            )
        
        # Return plan and artifacts
        return {
            "plan": final_state.plan,
            "artifacts": final_state.artifacts,
            "elapsed_time_sec": round(elapsed_time, 3)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error applying option: {str(e)}")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

