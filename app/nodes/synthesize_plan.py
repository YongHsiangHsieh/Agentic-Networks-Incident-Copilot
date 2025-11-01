"""
Node: Generate deployment plan with rollback capability.
"""

from app.models import IncidentState


def synthesize_plan(state: IncidentState) -> IncidentState:
    """
    Generate a deployment plan for the recommended remediation.
    
    Creates a structured plan with configuration details and
    a rollback tag for safety.
    
    Args:
        state: Current incident state with recommendation
        
    Returns:
        Updated state with plan generated
    """
    if state.error:
        return state
    
    if not state.recommendation:
        # No valid recommendation, skip plan generation
        return state
    
    try:
        recommendation = state.recommendation
        incident_id = state.incident_id
        
        # Generate rollback tag
        rollback_tag = f"{incident_id}_RB"
        
        # Create plan structure based on recommendation type
        plan_json = {
            "version": "1.0",
            "incident_id": incident_id,
            "action": recommendation.kind,
            "option_id": recommendation.id,
            "parameters": {},
            "estimated_duration_minutes": recommendation.eta_minutes,
            "risk_level": recommendation.risk,
            "pre_checks": [
                "Verify hot path topology",
                "Backup current configuration",
                "Tag snapshot with rollback identifier"
            ],
            "steps": [],
            "post_checks": [
                "Monitor latency for 5 minutes",
                "Verify packet loss < 0.5%",
                "Check service health endpoints"
            ],
            "rollback_procedure": f"Apply rollback tag {rollback_tag}"
        }
        
        # Add specific parameters and steps based on remediation type
        if recommendation.kind == "partial_offload":
            # Extract offload percentage from playbook
            plan_json["parameters"] = {
                "offload_percentage": 40,
                "target_path": "alternate_route_1"
            }
            plan_json["steps"] = [
                "Calculate traffic split ratio",
                "Update routing weights for 40% offload",
                "Apply configuration to edge routers",
                "Verify traffic distribution"
            ]
        
        elif recommendation.kind == "qos_shaping":
            plan_json["parameters"] = {
                "throttle_percentage": 20,
                "traffic_class": "bulk"
            }
            plan_json["steps"] = [
                "Identify bulk traffic flows",
                "Configure QoS policies with 20% throttle",
                "Apply to hot path interfaces",
                "Monitor queue depths"
            ]
        
        elif recommendation.kind == "burst_capacity":
            plan_json["parameters"] = {
                "capacity_gbps": 10,
                "duration_hours": 1,
                "cost_per_hour_eur": recommendation.euro_delta
            }
            plan_json["steps"] = [
                "Request burst capacity from provider",
                "Wait for capacity provisioning (2-3 min)",
                "Update path bandwidth allocations",
                "Verify increased throughput"
            ]
        
        state.plan = {
            "plan_json": plan_json,
            "rollback_tag": rollback_tag
        }
        
    except Exception as e:
        state.error = f"Error synthesizing plan: {str(e)}"
    
    return state

