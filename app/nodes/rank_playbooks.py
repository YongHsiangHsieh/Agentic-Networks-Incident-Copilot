"""
Node: Rank available playbooks based on predicted effectiveness.
"""

from app.models import IncidentState, CandidateOption
from app.playbooks import PLAYBOOKS, get_playbook_cost
from app.simulator import project


def rank_playbooks(state: IncidentState) -> IncidentState:
    """
    Evaluate and rank available remediation playbooks.
    
    For each playbook:
    1. Simulate predicted metrics using the simulator
    2. Calculate cost
    3. Create a CandidateOption
    
    Args:
        state: Current incident state
        
    Returns:
        Updated state with candidates list
    """
    if state.error:
        return state
    
    try:
        signals = state.signals
        bundle = state.bundle
        
        # Extract current metrics
        lat_now = signals.get("current_latency_ms")
        baseline = signals.get("baseline_latency_ms")
        loss_now = signals.get("current_loss_pct")
        util_peak = signals.get("util_peak", 0)
        
        candidates = []
        
        for playbook in PLAYBOOKS:
            # Project post-remediation metrics
            projection = project(
                lat_now=lat_now,
                baseline=baseline,
                loss_now=loss_now,
                util_peak=util_peak,
                option=playbook,
                baseline_ms=baseline
            )
            
            # Calculate cost
            euro_delta = get_playbook_cost(playbook, bundle.prices_eur)
            
            # Create candidate
            candidate = CandidateOption(
                id=playbook["id"],
                kind=playbook["kind"],
                eta_minutes=playbook["eta_minutes"],
                pred_latency_ms=projection["latency_ms"],
                pred_loss_pct=projection["loss_pct"],
                risk=playbook["risk"],
                euro_delta=euro_delta,
                policy_verdict={},  # Will be filled by policy_gate node
                explanation=None  # Optional, filled by justify_with_runbooks
            )
            
            candidates.append(candidate)
        
        # Sort by predicted latency (lower is better)
        candidates.sort(key=lambda c: c.pred_latency_ms)
        
        state.candidates = candidates
        
    except Exception as e:
        state.error = f"Error ranking playbooks: {str(e)}"
    
    return state

