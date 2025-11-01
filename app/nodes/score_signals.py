"""
Node: Score and analyze signal deltas.
"""

from app.models import IncidentState


def score_signals(state: IncidentState) -> IncidentState:
    """
    Compute signal deltas and utilization peaks.
    
    Calculates the change in latency and loss from baseline to current,
    and identifies peak utilization.
    
    Args:
        state: Current incident state with signals populated
        
    Returns:
        Updated state with scored signals
    """
    if state.error:
        return state
    
    try:
        signals = state.signals
        
        # Compute deltas
        delta_latency_ms = signals["current_latency_ms"] - signals["baseline_latency_ms"]
        delta_loss_pct = signals["current_loss_pct"] - signals["baseline_loss_pct"]
        
        # Find maximum utilization across all segments
        util_peaks = signals["current_util_peaks"]
        util_peak = max(util_peaks.values()) if util_peaks else 0.0
        
        # Add computed values to signals
        signals["delta_latency_ms"] = delta_latency_ms
        signals["delta_loss_pct"] = delta_loss_pct
        signals["util_peak"] = util_peak
        
        state.signals = signals
        
    except Exception as e:
        state.error = f"Error scoring signals: {str(e)}"
    
    return state

