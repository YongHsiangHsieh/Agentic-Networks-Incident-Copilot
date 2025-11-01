"""
Node: Ingest and validate incident bundle.
"""

from app.models import IncidentState


def ingest_bundle(state: IncidentState) -> IncidentState:
    """
    Validate bundle and compute baseline metrics.
    
    Computes baseline metrics from the first entry of the time series
    and current metrics from the last entry.
    
    Args:
        state: Current incident state
        
    Returns:
        Updated state with signals populated
    """
    try:
        bundle = state.bundle
        metrics = bundle.metrics
        
        # Validate that we have metrics
        if not metrics.latency_ms or not metrics.loss_pct:
            state.error = "Invalid metrics: latency_ms or loss_pct is empty"
            return state
        
        # Compute baseline (first entry) and current (last entry)
        baseline_latency_ms = metrics.latency_ms[0]
        baseline_loss_pct = metrics.loss_pct[0]
        current_latency_ms = metrics.latency_ms[-1]
        current_loss_pct = metrics.loss_pct[-1]
        
        # Compute utilization peaks across all segments
        current_util_peaks = {}
        for segment, util_series in metrics.util_pct.items():
            if util_series:
                current_util_peaks[segment] = max(util_series)
        
        # Store in state.signals
        state.signals = {
            "baseline_latency_ms": baseline_latency_ms,
            "baseline_loss_pct": baseline_loss_pct,
            "current_latency_ms": current_latency_ms,
            "current_loss_pct": current_loss_pct,
            "current_util_peaks": current_util_peaks
        }
        
    except Exception as e:
        state.error = f"Error ingesting bundle: {str(e)}"
    
    return state

