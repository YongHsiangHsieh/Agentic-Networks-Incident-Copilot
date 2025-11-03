# MCP Tools

## Direct MCP Tools (`mcp_server/server.py`)
- diagnose_incident(hot_path, latency_current, loss_current, ...)
- recommend_actions(root_cause, confidence, hot_path, ...)
- show_commands(playbook_id, hot_path, ...)
- generate_rca(incident_id, timestamp_start, hot_path, metrics, actions_taken, resolution_summary)

## LangGraph MCP Tools (`mcp_server/langgraph_server.py`)
- start_incident_workflow(incident_id, hot_path, latency_current, loss_current, ...)
- get_workflow_status(incident_id)
- approve_diagnosis(incident_id, approved, feedback, approved_by)
- approve_commands(incident_id, approved, feedback, approved_by)
- get_workflow_history(incident_id)
- select_playbook(incident_id, playbook_id)

See also: [MCP Setup](MCP-Setup.md).

