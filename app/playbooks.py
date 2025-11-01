"""
Playbook definitions for network incident remediation.
"""

PLAYBOOKS = [
    {
        "id": "opt_partial_offload_40",
        "kind": "partial_offload",
        "offload_pct": 40,
        "eta_minutes": 3,
        "risk": "low",
        "cost_per_hr_eur": 0
    },
    {
        "id": "opt_qos_shape_bulk_20",
        "kind": "qos_shaping",
        "throttle_pct": 20,
        "eta_minutes": 5,
        "risk": "medium",
        "cost_per_hr_eur": 0
    },
    {
        "id": "opt_burst_10gbps",
        "kind": "burst_capacity",
        "gbps": 10,
        "eta_minutes": 4,
        "risk": "low",
        # cost_per_hr_eur will be computed at runtime based on prices
        "cost_per_hr_eur": None  # placeholder, computed dynamically
    }
]


def get_playbook_cost(playbook: dict, prices) -> float:
    """
    Calculate the actual cost for a playbook given current prices.
    
    Args:
        playbook: Playbook definition dict
        prices: Prices model with pricing information
        
    Returns:
        Cost per hour in EUR
    """
    if playbook["kind"] == "burst_capacity":
        return prices.burst_capacity_per_1Gbps_hr * playbook["gbps"]
    return playbook.get("cost_per_hr_eur", 0)

