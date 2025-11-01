"""
Simple metrics projection engine for simulating remediation effects.
"""


def project(
    lat_now: float,
    baseline: float,
    loss_now: float,
    util_peak: float,
    option: dict,
    baseline_ms: float
) -> dict:
    """
    Project post-remediation metrics based on current state and chosen option.
    
    Uses deterministic formulas to simulate the effect of different remediation
    strategies on latency and packet loss.
    
    Args:
        lat_now: Current latency in ms
        baseline: Baseline latency in ms
        loss_now: Current packet loss percentage
        util_peak: Peak utilization percentage
        option: Playbook option dict with kind and parameters
        baseline_ms: Baseline latency (duplicate of baseline for compatibility)
        
    Returns:
        dict with predicted latency_ms and loss_pct
    """
    kind = option.get("kind")
    
    if kind == "partial_offload":
        # Offloading traffic reduces congestion
        k1 = 0.6
        offload_pct = option.get("offload_pct", 0)
        pred_latency = max(baseline, lat_now - k1 * (offload_pct / 10.0))
        pred_loss = max(0.1, loss_now - 0.8)
        return {
            "latency_ms": pred_latency,
            "loss_pct": pred_loss
        }
    
    elif kind == "qos_shaping":
        # QoS shaping throttles bulk traffic
        k2 = 0.4
        throttle_pct = option.get("throttle_pct", 0)
        pred_latency = max(baseline + 3, lat_now - k2 * (throttle_pct / 10.0))
        pred_loss = max(0.2, loss_now - 0.5)
        return {
            "latency_ms": pred_latency,
            "loss_pct": pred_loss
        }
    
    elif kind == "burst_capacity":
        # Burst capacity adds bandwidth, fully resolves congestion
        return {
            "latency_ms": baseline,
            "loss_pct": 0.2
        }
    
    # Default: no change
    return {
        "latency_ms": lat_now,
        "loss_pct": loss_now
    }


def generate_after_series(
    before_series: list,
    after_value: float,
    num_points: int = 10
) -> list:
    """
    Generate simulated 'after' time series showing gradual improvement.
    
    Args:
        before_series: Original time series data
        after_value: Target value after remediation
        num_points: Number of points in the after series
        
    Returns:
        List of values showing transition to after_value
    """
    if not before_series:
        return [after_value] * num_points
    
    start_value = before_series[-1]
    # Gradual transition from current to predicted
    step = (after_value - start_value) / num_points
    
    return [start_value + step * i for i in range(1, num_points + 1)]

