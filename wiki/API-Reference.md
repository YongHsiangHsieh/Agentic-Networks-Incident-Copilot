# API Reference

Production workflow endpoints (`app/api/workflow_endpoints.py`). Base path: `/api/workflows`.

- POST `/start` → Start workflow to first approval gate
- GET `/{incident_id}/status` → Current state summary
- POST `/{incident_id}/approve-diagnosis` → Resume to recommendations/commands
- POST `/{incident_id}/approve-commands` → Execute (simulated) + generate RCA
- GET `/{incident_id}/history` → Full audit trail
- POST `/{incident_id}/select-playbook` → Override playbook
- GET `/health` → Health check

Legacy utilities in `app/main.py`: `/diagnose`, `/recommend`, `/commands`, `/generate_rca`, `/full_workflow` (useful for demos/testing).

See also: [LangGraph Workflow](LangGraph-Workflow.md).

