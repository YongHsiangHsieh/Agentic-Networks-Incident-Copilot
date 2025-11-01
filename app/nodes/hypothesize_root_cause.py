"""
Node: Generate root cause hypothesis based on signals.
"""

from app.models import IncidentState


def hypothesize_root_cause(state: IncidentState) -> IncidentState:
    """
    Generate hypothesis about incident root cause.
    
    Uses rule-based logic to identify likely causes:
    - Congestion: high latency + high loss + high utilization
    - Config regression: recent configuration change
    
    Args:
        state: Current incident state with signals and change_context
        
    Returns:
        Updated state with hypothesis populated
    """
    if state.error:
        return state
    
    try:
        signals = state.signals
        change_context = state.change_context
        
        delta_latency_ms = signals.get("delta_latency_ms", 0)
        delta_loss_pct = signals.get("delta_loss_pct", 0)
        util_peak = signals.get("util_peak", 0)
        recent_change = change_context.get("recent_change", False)
        
        # Apply rules to determine root cause
        hypothesis = {}
        
        # Rule 1: Congestion detection
        if delta_latency_ms > 25 and delta_loss_pct > 1.0 and util_peak >= 90:
            hypothesis = {
                "cause": "congestion",
                "confidence": 0.8,
                "details": "High latency, packet loss, and utilization indicate network congestion"
            }
        # Rule 2: Config change correlation
        elif recent_change:
            hypothesis = {
                "cause": "config_regression",
                "confidence": 0.6,
                "details": "Recent configuration change detected in hot path"
            }
        # Rule 3: Moderate degradation
        elif delta_latency_ms > 10 and util_peak >= 70:
            hypothesis = {
                "cause": "congestion",
                "confidence": 0.6,
                "details": "Moderate latency increase with elevated utilization"
            }
        else:
            # Default: unknown degradation
            hypothesis = {
                "cause": "unknown_degradation",
                "confidence": 0.4,
                "details": "Service degradation detected but cause unclear"
            }
        
        # If we have both congestion and recent change, add alternate hypothesis
        if hypothesis.get("cause") == "congestion" and recent_change:
            hypothesis["alternate_cause"] = {
                "cause": "config_regression",
                "confidence": 0.6,
                "details": "Recent config change may have contributed"
            }
        
        state.hypothesis = hypothesis
        
    except Exception as e:
        state.error = f"Error generating hypothesis: {str(e)}"
    
    return state

