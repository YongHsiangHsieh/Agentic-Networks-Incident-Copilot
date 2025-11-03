# LangGraph Workflow

Consolidates `langgraph_orchestrator/*`, `LANGGRAPH_IMPLEMENTATION_COMPLETE.md`.

## Nodes
- diagnose → review_diagnosis (interrupt) → recommend → generate_commands → review_commands (interrupt) → execute → generate_rca → END

## State (`IncidentState`)
- Inputs: `incident_id`, `incident_data`
- Diagnosis: `diagnosis`, `diagnosis_confidence`, approvals/feedback
- Recommendations & selection
- Commands: generated output, approvals, feedback, modifications
- Execution: result, status, timestamp
- RCA: `rca_report`, `rca_generated_at`
- Workflow meta: `current_step`, `workflow_status`, `retry_count`
- Audit: `history`, `approvals`, `errors`

## Routing
- After diagnosis review: approved | retry | stop
- After commands review: execute | modify | stop
- After execution: rca | retry | stop

## Persistence
- Default checkpointer: `MemorySaver`
- Interrupt points: `review_diagnosis`, `review_commands`

## API & MCP Integration
- REST: `/api/workflows/*` endpoints mirror the graph lifecycle
- MCP: tools in `mcp_server/langgraph_server.py` expose start/approve/status/history/select

See also: [Architecture](Architecture.md), [API Reference](API-Reference.md).

