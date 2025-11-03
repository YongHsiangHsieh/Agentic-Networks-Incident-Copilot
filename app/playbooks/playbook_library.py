"""
Comprehensive playbook library for network incident remediation.
Each playbook defines a tested, safe procedure for specific root causes.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Playbook(BaseModel):
    """A remediation playbook with all necessary details for safe execution"""
    
    id: str = Field(..., description="Unique playbook identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="What this playbook does")
    root_causes: List[str] = Field(..., description="Which diagnoses this addresses")
    risk_level: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    time_to_effect: str = Field(..., description="How long until it takes effect")
    estimated_impact: str = Field(..., description="Expected improvement")
    cost: str = Field(..., description="FREE, LOW, MEDIUM, HIGH")
    prerequisites: List[str] = Field(..., description="What's needed before executing")
    commands_template: str = Field(..., description="CLI command template")
    verification_steps: List[str] = Field(..., description="How to verify success")
    rollback_procedure: str = Field(..., description="How to undo if it fails")
    when_to_use: str = Field(..., description="Detailed usage guidance")
    when_not_to_use: str = Field(..., description="Important warnings")
    success_indicators: List[str] = Field(..., description="Metrics that show success")
    typical_success_rate: float = Field(..., description="Historical success rate 0.0-1.0")


# Playbook 1: QoS Traffic Shaping (for congestion)
PLAYBOOK_QOS_SHAPING = Playbook(
    id="qos_traffic_shaping",
    name="QoS Traffic Shaping",
    description="Apply Quality of Service policies to prioritize critical traffic and limit bulk data during congestion",
    root_causes=["congestion", "high_latency", "packet_loss"],
    risk_level="LOW",
    time_to_effect="10 minutes",
    estimated_impact="Reduce latency by 50-70%, packet loss by 60-80%",
    cost="FREE",
    prerequisites=[
        "Admin access to router",
        "QoS policies defined",
        "Non-peak hours preferred (but works during peak)",
    ],
    commands_template="""
# QoS Traffic Shaping for {hot_path}
# Expected impact: Reduce latency by ~60% in 10 minutes

# Step 1: Backup current configuration
ssh admin@{router_source}
copy running-config backup-{timestamp}.cfg
exit

# Step 2: Apply QoS policy to congested interface
ssh admin@{router_source}
configure terminal
interface {interface_id}
  service-policy output QOS_PEAK_HOURS
  bandwidth percent 60
  priority-queue out
  queue-limit 1000
end
write memory
exit

# Step 3: Verify QoS is active
show policy-map interface {interface_id}
show interface {interface_id} | include queue

# Step 4: Monitor for 10 minutes
# Expected: Latency {current_latency}ms → ~{expected_latency}ms
# Expected: Loss {current_loss}% → ~{expected_loss}%
""",
    verification_steps=[
        "Check QoS policy is applied: show policy-map interface",
        "Monitor latency for 10 minutes, expect 50-70% reduction",
        "Monitor packet loss, expect 60-80% reduction",
        "Verify no new errors: show interface errors",
        "Check that priority traffic is not degraded",
    ],
    rollback_procedure="""
# Rollback: Remove QoS policy
ssh admin@{router_source}
configure terminal
interface {interface_id}
  no service-policy output
end
write memory
exit

# Restore from backup if needed
copy backup-{timestamp}.cfg running-config
""",
    when_to_use="Peak hour congestion with mixed traffic types. Utilization >70%. Latency and loss elevated but not catastrophic. Need gradual, safe improvement.",
    when_not_to_use="Hardware failures, configuration errors, routing issues. QoS won't help if the problem is not traffic-related. Don't use if all traffic is equally critical.",
    success_indicators=[
        "Latency drops by >50% within 10 minutes",
        "Packet loss drops by >60% within 10 minutes",
        "Priority traffic maintains SLA",
        "No new interface errors",
    ],
    typical_success_rate=0.85,
)


# Playbook 2: Partial Traffic Offload (for congestion)
PLAYBOOK_TRAFFIC_OFFLOAD = Playbook(
    id="partial_traffic_offload",
    name="Partial Traffic Offload",
    description="Redistribute portion of traffic to alternate path to relieve congestion immediately",
    root_causes=["congestion", "high_latency"],
    risk_level="MEDIUM",
    time_to_effect="2 minutes",
    estimated_impact="Reduce latency by 70-85%, packet loss by 80-95%",
    cost="FREE",
    prerequisites=[
        "Alternate path available",
        "Alternate path has capacity",
        "Routing protocol supports redistribution",
        "Change window approved",
    ],
    commands_template="""
# Partial Traffic Offload from {hot_path} to alternate path
# WARNING: May cause brief traffic disruption during cutover

# Step 1: Verify alternate path availability
ssh admin@{router_source}
show ip route {destination_network}
show interface {alternate_interface} | include utilization
# Ensure alternate path has <50% utilization

# Step 2: Configure traffic redistribution (50% offload)
configure terminal
router bgp {asn}
  address-family ipv4
    network {destination_network} backdoor {alternate_next_hop}
    maximum-paths 2
  exit-address-family
end
write memory

# Step 3: Monitor traffic shift
show ip bgp {destination_network}
show interface {interface_id} statistics
# Traffic should split ~50/50 within 1-2 minutes

# Step 4: Verify metrics
# Expected: Latency {current_latency}ms → ~{expected_latency}ms
# Expected: Loss {current_loss}% → ~{expected_loss}%
""",
    verification_steps=[
        "Check traffic is splitting across paths: show ip route",
        "Monitor latency on primary path, expect 70-85% reduction",
        "Verify alternate path is handling load well (utilization <80%)",
        "Check for packet reordering issues",
        "Verify no routing loops: traceroute",
    ],
    rollback_procedure="""
# Rollback: Remove traffic offload
ssh admin@{router_source}
configure terminal
router bgp {asn}
  address-family ipv4
    no maximum-paths
    no network {destination_network} backdoor
  exit-address-family
end
write memory
""",
    when_to_use="Severe congestion requiring immediate relief. Alternate path is available and healthy. Traffic can tolerate brief disruption. Time-sensitive situation.",
    when_not_to_use="No alternate path available. Alternate path already congested. Path asymmetry causes issues. During peak revenue hours without approval.",
    success_indicators=[
        "Latency drops by >70% within 2 minutes",
        "Packet loss drops by >80% within 2 minutes",
        "Traffic evenly distributed across paths",
        "No packet reordering or out-of-sequence issues",
    ],
    typical_success_rate=0.78,
)


# Playbook 3: Configuration Rollback (for config issues)
PLAYBOOK_CONFIG_ROLLBACK = Playbook(
    id="config_rollback",
    name="Configuration Rollback",
    description="Revert recent configuration change that caused the incident",
    root_causes=["config_change", "routing_issue", "degradation_after_change"],
    risk_level="LOW",
    time_to_effect="1 minute",
    estimated_impact="Full restoration if config change was root cause",
    cost="FREE",
    prerequisites=[
        "Recent config change identified",
        "Backup configuration available",
        "Change correlation confirmed",
    ],
    commands_template="""
# Configuration Rollback for {hot_path}
# Rolling back change made at {change_timestamp}

# Step 1: Identify the problematic change
ssh admin@{router_source}
show archive config differences nvram:startup-config system:running-config
show configuration commit list

# Step 2: Rollback to previous working config
configure replace {backup_config_path} force
# OR
rollback configuration to id {commit_id}

# Step 3: Verify rollback successful
show running-config | include {changed_section}
show ip route | include {affected_routes}

# Step 4: Verify metrics restored
# Expected: Latency back to {baseline_latency}ms
# Expected: Loss back to {baseline_loss}%
""",
    verification_steps=[
        "Confirm configuration matches pre-change state",
        "Check routing table is correct: show ip route",
        "Monitor latency, expect return to baseline within 1-2 minutes",
        "Monitor packet loss, expect return to baseline",
        "Verify all expected routes are present",
    ],
    rollback_procedure="""
# If rollback causes issues, re-apply the change:
configure replace {original_config_path} force
# Or restore from backup:
copy backup-{timestamp}.cfg running-config
""",
    when_to_use="Incident started immediately after configuration change. Metrics were normal before change. Change correlation is clear. Quick restoration needed.",
    when_not_to_use="Change was hours ago and metrics were fine initially. Multiple changes occurred. Root cause is actually hardware or external. Change was required for security.",
    success_indicators=[
        "Metrics return to baseline within 1-2 minutes",
        "Routing table restored to pre-change state",
        "No new errors or alarms",
        "Services fully operational",
    ],
    typical_success_rate=0.92,
)


# Playbook 4: Hardware Diagnostics & Replacement (for hardware issues)
PLAYBOOK_HARDWARE_REPLACE = Playbook(
    id="hardware_diagnostics_replace",
    name="Hardware Diagnostics & Replacement",
    description="Diagnose hardware failure and execute emergency replacement or failover",
    root_causes=["hardware_failure", "interface_errors", "line_card_failure"],
    risk_level="HIGH",
    time_to_effect="15-30 minutes (diagnostics) or 2-4 hours (replacement)",
    estimated_impact="Full restoration if hardware is replaceable; 100% if failover works",
    cost="HIGH (replacement hardware cost)",
    prerequisites=[
        "Physical access to equipment or remote hands",
        "Spare hardware available",
        "Backup path for traffic rerouting",
        "Change approval for hardware replacement",
    ],
    commands_template="""
# Hardware Diagnostics for {hot_path}
# Suspected hardware failure on {suspected_component}

# Step 1: Run comprehensive diagnostics
ssh admin@{router_source}
show diagnostic result module {module_id}
show environment all
show interfaces {interface_id} transceiver details
show hardware

# Step 2: Check for hardware errors
show interfaces {interface_id} | include error|CRC|drop
show logging | include {interface_id}|hardware|failure
show platform hardware

# Step 3: If hardware failure confirmed, reroute traffic FIRST
configure terminal
interface {interface_id}
  shutdown
exit
router {routing_protocol}
  redistribute static route {affected_routes} via {alternate_path}
end
write memory

# Step 4: Coordinate hardware replacement
# [Manual step: physical replacement or RMA process]
# Expected downtime: 2-4 hours

# Step 5: After replacement, verify and restore
interface {interface_id}
  no shutdown
end
# Run diagnostics again to confirm health
""",
    verification_steps=[
        "Diagnostic tests pass with no errors",
        "Interface shows no CRC errors or frame errors",
        "Transceiver power levels within normal range",
        "Temperature within acceptable limits",
        "Traffic successfully rerouted during replacement",
        "After replacement: full connectivity restored",
    ],
    rollback_procedure="""
# If replacement causes issues:
# 1. Re-shutdown the problematic interface
interface {interface_id}
  shutdown
end

# 2. Restore traffic to original backup path
# 3. Investigate replacement hardware
# 4. May need to revert to original (failing) hardware temporarily
""",
    when_to_use="Clear hardware failure indicators (CRC errors, interface down, diagnostic failures). High packet loss with normal utilization. Physical layer issues. Transceiver failures.",
    when_not_to_use="Software/configuration issues. No hardware errors in logs. Network-layer problems. When quick resolution is critical (use failover instead of replacement).",
    success_indicators=[
        "Hardware diagnostics pass completely",
        "Interface errors drop to zero",
        "Latency and loss return to baseline",
        "No environmental alarms (temperature, power)",
        "Stable operation for 24+ hours",
    ],
    typical_success_rate=0.88,
)


# Playbook 5: Route Redistribution (for routing issues)
PLAYBOOK_ROUTE_REDISTRIBUTION = Playbook(
    id="route_redistribution",
    name="Route Redistribution & Path Optimization",
    description="Fix routing issues by redistributing routes or adjusting path preferences",
    root_causes=["routing_issue", "suboptimal_path", "route_flap"],
    risk_level="MEDIUM",
    time_to_effect="2-5 minutes",
    estimated_impact="Optimal path restoration, latency reduction by 40-60%",
    cost="FREE",
    prerequisites=[
        "Routing protocol knowledge (BGP/OSPF/EIGRP)",
        "Understanding of network topology",
        "Correct path identified",
    ],
    commands_template="""
# Route Redistribution for {hot_path}
# Optimizing path selection for {destination_network}

# Step 1: Analyze current routing
ssh admin@{router_source}
show ip route {destination_network}
show ip bgp {destination_network}
show ip ospf database
traceroute {destination_ip}

# Step 2: Identify optimal path
# Current path: {current_path}
# Optimal path: {optimal_path}

# Step 3: Adjust routing metrics/preferences
configure terminal
router {routing_protocol}
  # For BGP: adjust local preference or MED
  neighbor {peer_ip} route-map {route_map_name} in
  # For OSPF: adjust cost
  interface {interface_id}
    ip ospf cost {new_cost}
exit
route-map {route_map_name} permit 10
  match ip address prefix-list {prefix_list}
  set local-preference {higher_preference}
end
write memory

# Step 4: Verify route change
show ip route {destination_network}
traceroute {destination_ip}
# Verify path now goes through {optimal_path}

# Step 5: Monitor metrics
# Expected: Latency {current_latency}ms → ~{expected_latency}ms
""",
    verification_steps=[
        "Routing table shows preferred path: show ip route",
        "Traceroute confirms traffic uses optimal path",
        "BGP/OSPF neighbors remain stable (no flapping)",
        "Latency improves by 40-60%",
        "No routing loops detected",
    ],
    rollback_procedure="""
# Rollback routing changes
ssh admin@{router_source}
configure terminal
router {routing_protocol}
  no neighbor {peer_ip} route-map {route_map_name} in
interface {interface_id}
  no ip ospf cost
end
no route-map {route_map_name}
write memory
""",
    when_to_use="Suboptimal routing paths. Route flapping causing instability. Path asymmetry issues. BGP path selection needs tuning. OSPF cost misconfiguration.",
    when_not_to_use="Physical layer issues. Hardware failures. Configuration errors unrelated to routing. When network topology doesn't support alternate paths.",
    success_indicators=[
        "Traffic follows optimal path consistently",
        "Latency reduces by 40-60%",
        "No route flapping (stable for 10+ minutes)",
        "BGP/OSPF neighbors stable",
    ],
    typical_success_rate=0.81,
)


# Playbook 6: Emergency Capacity Upgrade (for persistent congestion)
PLAYBOOK_EMERGENCY_CAPACITY = Playbook(
    id="emergency_capacity_upgrade",
    name="Emergency Capacity Upgrade",
    description="Provision additional bandwidth or activate reserved capacity for persistent congestion",
    root_causes=["persistent_congestion", "capacity_exhaustion"],
    risk_level="HIGH",
    time_to_effect="30 minutes - 4 hours (depending on provider)",
    estimated_impact="Full congestion relief, latency normalized, loss eliminated",
    cost="HIGH (bandwidth cost increases)",
    prerequisites=[
        "Budget approval for capacity increase",
        "ISP/carrier coordination",
        "Reserved capacity contract OR emergency provisioning available",
        "Other remediation attempts failed",
    ],
    commands_template="""
# Emergency Capacity Upgrade for {hot_path}
# WARNING: This involves ISP coordination and cost implications

# Step 1: Coordinate with ISP/carrier
# [Manual step: Contact carrier NOC]
# Request: Upgrade {circuit_id} from {current_bandwidth} to {new_bandwidth}
# OR: Activate pre-provisioned reserve capacity

# Step 2: Once carrier confirms upgrade, verify on router
ssh admin@{router_source}
show interface {interface_id} | include BW
# Should show new bandwidth

# Step 3: Adjust IGP metrics if needed
configure terminal
interface {interface_id}
  bandwidth {new_bandwidth_kbps}
end
write memory

# Step 4: Verify capacity increase
show interface {interface_id} statistics
# Utilization should drop significantly

# Step 5: Monitor for sustained improvement
# Expected: Utilization {current_util}% → <50%
# Expected: Latency {current_latency}ms → ~{baseline_latency}ms
# Expected: Loss {current_loss}% → ~0%
""",
    verification_steps=[
        "Interface shows increased bandwidth: show interface",
        "Utilization drops below 50%",
        "Latency returns to baseline",
        "Packet loss drops to near-zero",
        "Sustained improvement over 24 hours",
    ],
    rollback_procedure="""
# Rollback (usually not desired due to cost):
# Coordinate with ISP to downgrade bandwidth
# This typically requires contract renegotiation
# Usually not immediate - may take days/weeks
""",
    when_to_use="Persistent congestion despite QoS and offloading. Utilization consistently >85%. Traffic growth exceeds current capacity. Critical business impact. Long-term solution needed.",
    when_not_to_use="Temporary traffic spikes. Other solutions haven't been tried. Budget not approved. Congestion caused by inefficient routing (optimize first).",
    success_indicators=[
        "Utilization drops below 50% and stays there",
        "Latency returns to baseline permanently",
        "Packet loss eliminated",
        "No congestion even during peak hours",
    ],
    typical_success_rate=0.95,
)


# All playbooks in priority order
ALL_PLAYBOOKS = [
    PLAYBOOK_QOS_SHAPING,
    PLAYBOOK_TRAFFIC_OFFLOAD,
    PLAYBOOK_CONFIG_ROLLBACK,
    PLAYBOOK_HARDWARE_REPLACE,
    PLAYBOOK_ROUTE_REDISTRIBUTION,
    PLAYBOOK_EMERGENCY_CAPACITY,
]


def get_playbook_by_id(playbook_id: str) -> Optional[Playbook]:
    """Get a specific playbook by ID"""
    for playbook in ALL_PLAYBOOKS:
        if playbook.id == playbook_id:
            return playbook
    return None


def get_playbooks_for_root_cause(root_cause: str) -> List[Playbook]:
    """Get all playbooks that address a specific root cause"""
    matching = []
    for playbook in ALL_PLAYBOOKS:
        if root_cause.lower() in [rc.lower() for rc in playbook.root_causes]:
            matching.append(playbook)
    return matching

