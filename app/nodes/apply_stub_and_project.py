"""
Node: Simulate application of remediation and project metrics.
"""

from app.models import IncidentState
from app.simulator import generate_after_series


def apply_stub_and_project(state: IncidentState) -> IncidentState:
    """
    Simulate the application of remediation and project future metrics.
    
    Uses the simulator to generate "after" time series showing
    the predicted improvement in latency and loss.
    
    Args:
        state: Current incident state with recommendation and plan
        
    Returns:
        Updated state with projected metrics stored for artifact generation
    """
    if state.error:
        return state
    
    if not state.recommendation or not state.plan:
        return state
    
    try:
        recommendation = state.recommendation
        bundle = state.bundle
        
        # Get before metrics
        before_latency = bundle.metrics.latency_ms
        before_loss = bundle.metrics.loss_pct
        
        # Generate after series based on predictions
        after_latency = generate_after_series(
            before_series=before_latency,
            after_value=recommendation.pred_latency_ms,
            num_points=10
        )
        
        after_loss = generate_after_series(
            before_series=before_loss,
            after_value=recommendation.pred_loss_pct,
            num_points=10
        )
        
        # Store projected series in state for artifact generation
        if not state.artifacts:
            state.artifacts = {}
        
        state.artifacts["before_latency"] = before_latency
        state.artifacts["after_latency"] = after_latency
        state.artifacts["before_loss"] = before_loss
        state.artifacts["after_loss"] = after_loss
        
    except Exception as e:
        state.error = f"Error projecting metrics: {str(e)}"
    
    return state

