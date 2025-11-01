"""
Policy enforcement logic for remediation options.
"""

from app.models import CandidateOption, Policy, Prices


def check(candidate: CandidateOption, policy: Policy, prices: Prices) -> dict:
    """
    Validate a candidate option against operational policies.
    
    Args:
        candidate: The remediation option to check
        policy: Policy constraints to enforce
        prices: Pricing information for cost calculations
        
    Returns:
        dict with keys:
            - ok (bool): Whether the candidate passes all policy checks
            - reasons (list): List of failure reasons (empty if ok=True)
    """
    reasons = []
    
    # Check if predicted latency exceeds target
    if candidate.pred_latency_ms > policy.latency_target_ms:
        reasons.append(
            f"Predicted latency {candidate.pred_latency_ms}ms exceeds "
            f"target {policy.latency_target_ms}ms"
        )
    
    # Check if burst capacity cost exceeds budget
    if candidate.kind == "burst_capacity":
        if candidate.euro_delta > policy.max_burst_cost_per_hr_eur:
            reasons.append(
                f"Burst cost €{candidate.euro_delta:.2f}/hr exceeds "
                f"budget €{policy.max_burst_cost_per_hr_eur:.2f}/hr"
            )
    
    # partial_offload and qos_shaping are generally allowed if no cost violation
    # (they have 0 cost in the spec, so they won't violate cost constraints)
    
    return {
        "ok": len(reasons) == 0,
        "reasons": reasons
    }

