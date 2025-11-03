# Playbooks

Source: `app/playbooks/playbook_library.py`

## Library
- QoS Traffic Shaping (`qos_traffic_shaping`) — LOW risk, ~10m effect
- Partial Traffic Offload (`partial_traffic_offload`) — MEDIUM risk, ~2m effect
- Configuration Rollback (`config_rollback`) — LOW risk, ~1m effect
- Hardware Diagnostics & Replacement (`hardware_diagnostics_replace`) — HIGH risk
- Route Redistribution (`route_redistribution`) — MEDIUM risk, 2–5m
- Emergency Capacity Upgrade (`emergency_capacity_upgrade`) — HIGH cost, 30m–4h

Each playbook includes:
- Description, applicable root causes, risk, time to effect, cost, success rate
- Prerequisites, verification steps, rollback procedure, success indicators
- Commands template with parameters like `{interface_id}`, `{current_latency}`

Used by:
- Recommendation Engines for scoring and selection
- Command Generator for rendering safe commands

