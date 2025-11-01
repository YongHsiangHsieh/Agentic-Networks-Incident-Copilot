"""
Node: Enforce policy constraints and select recommendation.
"""

from app.models import IncidentState
from app.policy import check


def policy_gate(state: IncidentState) -> IncidentState:
    """
    Apply policy checks to all candidates and select recommendation.
    
    Evaluates each candidate against operational policies and selects
    the best option that passes all checks.
    
    Args:
        state: Current incident state with candidates
        
    Returns:
        Updated state with policy_verdicts and recommendation
    """
    if state.error or not state.candidates:
        return state
    
    try:
        bundle = state.bundle
        policy_verdicts = []
        passing_candidates = []
        
        # Check each candidate against policy
        for candidate in state.candidates:
            verdict = check(candidate, bundle.policy, bundle.prices_eur)
            
            # Update candidate with verdict
            candidate.policy_verdict = verdict
            policy_verdicts.append({
                "candidate_id": candidate.id,
                "verdict": verdict
            })
            
            if verdict["ok"]:
                passing_candidates.append(candidate)
        
        state.policy_verdicts = policy_verdicts
        
        # Select best passing candidate
        # Priority: lowest latency, then lowest cost, then lowest eta
        if passing_candidates:
            # Sort by: latency (lower is better), cost (lower is better), eta (lower is better)
            passing_candidates.sort(
                key=lambda c: (c.pred_latency_ms, c.euro_delta, c.eta_minutes)
            )
            state.recommendation = passing_candidates[0]
        else:
            state.recommendation = None
        
    except Exception as e:
        state.error = f"Error in policy gate: {str(e)}"
    
    return state

