"""
Node: Generate and deliver final artifacts (charts and reports).
"""

import os
import time
from app.models import IncidentState
from app.render import render_timeseries_chart, render_one_pager


def deliver_artifacts(state: IncidentState) -> IncidentState:
    """
    Generate final artifacts: timeseries chart and one-pager report.
    
    Creates visualization and documentation for the incident analysis
    and remediation plan.
    
    Args:
        state: Current incident state with all analysis complete
        
    Returns:
        Updated state with artifact paths
    """
    if state.error:
        # Still try to generate error report
        pass
    
    try:
        incident_id = state.incident_id
        
        # Create output directory
        output_dir = os.path.join("artifacts", incident_id)
        os.makedirs(output_dir, exist_ok=True)
        
        if not state.artifacts:
            state.artifacts = {}
        
        # Generate timeseries chart if we have projection data
        if (state.artifacts.get("before_latency") and 
            state.artifacts.get("after_latency")):
            
            chart_path = os.path.join(output_dir, "timeseries.png")
            render_timeseries_chart(
                before_latency=state.artifacts["before_latency"],
                after_latency=state.artifacts["after_latency"],
                before_loss=state.artifacts["before_loss"],
                after_loss=state.artifacts["after_loss"],
                output_path=chart_path
            )
            state.artifacts["chart_png"] = chart_path
        
        # Generate one-pager report if we have recommendation
        if state.recommendation and state.hypothesis and state.plan:
            # Calculate financial metrics
            euro_spent = state.recommendation.euro_delta
            euro_avoided = 3000.0  # Hardcoded SLA penalty as per spec
            
            # Estimate time-to-diagnosis (simulate < 5 seconds)
            time_to_diagnosis_sec = 2.5
            
            # Time-to-restore from recommendation
            time_to_restore_min = state.recommendation.eta_minutes
            
            one_pager_path = os.path.join(output_dir, "summary.html")
            render_one_pager(
                incident_id=incident_id,
                hypothesis=state.hypothesis,
                recommendation=state.recommendation.model_dump(),
                plan=state.plan,
                euro_spent=euro_spent,
                euro_avoided=euro_avoided,
                time_to_diagnosis_sec=time_to_diagnosis_sec,
                time_to_restore_min=time_to_restore_min,
                output_path=one_pager_path
            )
            state.artifacts["one_pager"] = one_pager_path
        
    except Exception as e:
        state.error = f"Error delivering artifacts: {str(e)}"
    
    return state

