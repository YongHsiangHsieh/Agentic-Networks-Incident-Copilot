# Incident Playbook Picker (IPP)

## Overview

The Incident Playbook Picker is an intelligent system that diagnoses network incidents, ranks remediation options, enforces policy gates, and generates actionable plans with rollback capabilities.

## Features

- **Automated Diagnosis**: Analyzes metrics and change events to identify root causes
- **Playbook Ranking**: Evaluates multiple remediation options with cost and risk analysis
- **Policy Enforcement**: Ensures recommendations comply with operational policies
- **Simulation**: Projects post-remediation metrics before application
- **Artifact Generation**: Produces charts and comprehensive one-pager reports

## Architecture

Built with:
- **Python 3.12+**
- **LangGraph 1.0** for orchestration
- **LangChain 1.0** for optional RAG explanations
- **FastAPI** for MCP-style tool endpoints
- **Matplotlib** for visualization
- **Jinja2** for templating

## Installation

### Prerequisites
- Python 3.12 or higher
- pip package manager

### Setup Steps

1. Clone the repository:
```bash
git clone <repository-url>
cd Agentic-Networks-Incident-Copilot
```

2. (Optional) Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server

Start the FastAPI server:

```bash
python3 -m uvicorn app.main:app --reload
```

Or if you prefer the shorter version (if uvicorn script is properly configured):

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000` or `http://127.0.0.1:8000`

Access the interactive API docs at `http://localhost:8000/docs`

## API Endpoints

### POST /diagnose_issue

Analyzes an incident and returns diagnosis with ranked remediation options.

**Request Body**: `IncidentBundle` JSON

**Response**:
```json
{
  "hypothesis": {
    "cause": "congestion",
    "confidence": 0.8
  },
  "candidates": [
    {
      "id": "opt_partial_offload_40",
      "kind": "partial_offload",
      "eta_minutes": 3,
      "pred_latency_ms": 45.0,
      "pred_loss_pct": 0.5,
      "risk": "low",
      "euro_delta": 0.0,
      "policy_verdict": {"ok": true, "reasons": []},
      "explanation": null
    }
  ],
  "policy_verdicts": [...]
}
```

### POST /apply_option

Applies a selected remediation option and generates artifacts.

**Request Body**:
```json
{
  "incident_id": "INC-20250101-001",
  "option_id": "opt_partial_offload_40"
}
```

**Response**:
```json
{
  "plan": {
    "plan_json": {...},
    "rollback_tag": "INC-20250101-001_RB"
  },
  "artifacts": {
    "chart_png": "artifacts/INC-20250101-001/timeseries.png",
    "one_pager": "artifacts/INC-20250101-001/summary.html"
  }
}
```

## Workflow Overview

The IPP system follows this workflow:

1. **Ingest Bundle** → Validate incident data and extract baseline metrics
2. **Score Signals** → Compute deltas in latency, loss, and utilization
3. **Correlate Changes** → Identify recent configuration changes
4. **Hypothesize Root Cause** → Apply rules to determine likely cause (congestion, config regression, etc.)
5. **Rank Playbooks** → Evaluate remediation options and predict outcomes
6. **Policy Gate** → Enforce operational policies and select best option
7. **Synthesize Plan** → Generate deployment plan with rollback tag
8. **Project Metrics** → Simulate post-remediation performance
9. **Deliver Artifacts** → Create charts and one-pager report

## Sample Usage

### Example 1: Basic Congestion Incident

Diagnose an incident with high utilization and no recent changes:

```bash
curl -X POST http://localhost:8000/diagnose_issue \
  -H "Content-Type: application/json" \
  -d @tests/test_incident_basic.json
```

**Sample Response:**
```json
{
  "hypothesis": {
    "cause": "congestion",
    "confidence": 0.8,
    "details": "High latency, packet loss, and utilization indicate network congestion"
  },
  "candidates": [
    {
      "id": "opt_burst_10gbps",
      "kind": "burst_capacity",
      "eta_minutes": 4,
      "pred_latency_ms": 35.0,
      "pred_loss_pct": 0.2,
      "risk": "low",
      "euro_delta": 150.0,
      "policy_verdict": {"ok": true, "reasons": []}
    },
    {
      "id": "opt_partial_offload_40",
      "kind": "partial_offload",
      "eta_minutes": 3,
      "pred_latency_ms": 45.6,
      "pred_loss_pct": 0.5,
      "risk": "low",
      "euro_delta": 0.0,
      "policy_verdict": {"ok": true, "reasons": []}
    }
  ],
  "recommendation": {
    "id": "opt_burst_10gbps",
    "kind": "burst_capacity"
  },
  "elapsed_time_sec": 0.142
}
```

### Example 2: Config Change Incident

Diagnose an incident with a recent configuration change:

```bash
curl -X POST http://localhost:8000/diagnose_issue \
  -H "Content-Type: application/json" \
  -d @tests/test_incident_configchange.json
```

This will detect the config change correlation and may suggest config_regression as the root cause.

### Example 3: Apply Selected Remediation

After diagnosing, apply the recommended option:

```bash
curl -X POST http://localhost:8000/apply_option \
  -H "Content-Type: application/json" \
  -d '{"incident_id": "INC-20250101-001", "option_id": "opt_partial_offload_40"}'
```

**Sample Response:**
```json
{
  "plan": {
    "plan_json": {
      "version": "1.0",
      "incident_id": "INC-20250101-001",
      "action": "partial_offload",
      "parameters": {
        "offload_percentage": 40,
        "target_path": "alternate_route_1"
      },
      "steps": [
        "Calculate traffic split ratio",
        "Update routing weights for 40% offload",
        "Apply configuration to edge routers",
        "Verify traffic distribution"
      ]
    },
    "rollback_tag": "INC-20250101-001_RB"
  },
  "artifacts": {
    "chart_png": "artifacts/INC-20250101-001/timeseries.png",
    "one_pager": "artifacts/INC-20250101-001/summary.html",
    "before_latency": [...],
    "after_latency": [...]
  },
  "elapsed_time_sec": 0.089
}
```

### Example 4: Using Python Requests

```python
import requests
import json

# Diagnose incident
with open('tests/test_incident_basic.json', 'r') as f:
    incident_data = json.load(f)

response = requests.post(
    'http://localhost:8000/diagnose_issue',
    json=incident_data
)

result = response.json()
print(f"Root cause: {result['hypothesis']['cause']}")
print(f"Recommendation: {result['recommendation']['id']}")

# Apply remediation
apply_response = requests.post(
    'http://localhost:8000/apply_option',
    json={
        'incident_id': incident_data['incident_id'],
        'option_id': result['recommendation']['id']
    }
)

artifacts = apply_response.json()
print(f"Plan created with rollback tag: {artifacts['plan']['rollback_tag']}")
print(f"One-pager available at: {artifacts['artifacts']['one_pager']}")
```

## Project Structure

```
/ipp_project/
  README.md
  requirements.txt
  /app/
    main.py                 # FastAPI entrypoint
    graph.py                # LangGraph setup
    models.py               # Pydantic data models
    playbooks.py            # Playbook definitions
    policy.py               # Policy enforcement logic
    simulator.py            # Metrics projection engine
    render.py               # Chart and report generation
    /nodes/                 # LangGraph node implementations
    /runbooks/              # Optional RAG corpus
  /tests/
    test_incident_basic.json
    test_incident_configchange.json
    test_graph_flow.py
  /artifacts/
    (auto-generated outputs)
```

## Testing

Run the complete test suite:

```bash
pytest tests/ -v
```

Run specific tests:

```bash
# Test basic workflow
pytest tests/test_graph_flow.py::test_basic_incident_flow -v

# Test policy enforcement
pytest tests/test_graph_flow.py::test_policy_failure_scenario -v

# Test config change detection
pytest tests/test_graph_flow.py::test_configchange_incident -v
```

Test coverage includes:
- Basic congestion incident flow
- Config change correlation
- Policy constraint enforcement
- Candidate ranking logic
- Metric projection accuracy
- End-to-end workflow with artifacts

## Artifacts

Generated artifacts are saved to `artifacts/{incident_id}/`:
- **`timeseries.png`**: Before/after metrics visualization showing latency and packet loss trends
- **`summary.html`**: Comprehensive one-pager report with:
  - Root cause hypothesis with confidence score
  - Recommended remediation with predicted metrics
  - Deployment plan with rollback procedure
  - Financial impact (cost vs SLA penalty avoided)
  - Time-to-diagnosis and time-to-restore estimates
  - Step-by-step implementation guide

To view artifacts, simply open the HTML file in a browser:
```bash
open artifacts/INC-20250101-001/summary.html
```

## Available Playbooks

The system includes three remediation strategies:

1. **Partial Offload** (`opt_partial_offload_40`)
   - Redirects 40% of traffic to alternate paths
   - ETA: 3 minutes
   - Risk: Low
   - Cost: €0/hr

2. **QoS Traffic Shaping** (`opt_qos_shape_bulk_20`)
   - Throttles bulk traffic by 20%
   - ETA: 5 minutes
   - Risk: Medium
   - Cost: €0/hr

3. **Burst Capacity** (`opt_burst_10gbps`)
   - Provisions 10 Gbps additional bandwidth
   - ETA: 4 minutes
   - Risk: Low
   - Cost: €150/hr (based on pricing)

## Performance Characteristics

- **Response time**: < 5 seconds for demo incidents
- **Time-to-diagnosis**: ~2.5 seconds (simulated)
- **Time-to-restore**: < 10 minutes (depends on selected playbook)
- **Deterministic logic**: No random seeds, reproducible results
- **Policy compliance**: 100% enforcement of operational constraints

## Extension Points

The system is designed for easy extension:

### Adding New Playbooks
Edit `app/playbooks.py` to add new remediation strategies:
```python
{
    "id": "opt_custom_strategy",
    "kind": "custom_strategy",
    "eta_minutes": 5,
    "risk": "medium",
    "cost_per_hr_eur": 50.0
}
```

Then update `app/simulator.py` to handle the new strategy type.

### Extending Policy Rules
Modify `app/policy.py` to add new constraints:
```python
# Example: Check minimum redundancy
if candidate.kind == "partial_offload":
    if get_available_paths() < policy.min_path_redundancy:
        reasons.append("Insufficient path redundancy")
```

### Adding RAG Context
Place additional runbook documents in `app/runbooks/`:
- Create `.txt` files with remediation procedures
- The system will automatically search and attach relevant explanations
- Enable by setting `include_justification=True` in `build_graph()`

### Customizing Nodes
Each node in `app/nodes/` can be modified independently:
- Add new data sources in `ingest_bundle.py`
- Enhance hypothesis logic in `hypothesize_root_cause.py`
- Add new metrics in `score_signals.py`

## Data Model Reference

### IncidentBundle Structure
```json
{
  "incident_id": "INC-YYYYMMDD-NNN",
  "window": {
    "start_ts": "ISO 8601 timestamp",
    "end_ts": "ISO 8601 timestamp"
  },
  "hot_path": "RouterA->RouterB->RouterC",
  "metrics": {
    "latency_ms": [35.0, 40.0, ...],
    "loss_pct": [0.1, 0.2, ...],
    "util_pct": {
      "segment_name": [75.0, 80.0, ...]
    }
  },
  "changes": [
    {
      "ts": "ISO 8601 timestamp",
      "type": "config_change|deployment",
      "scope": "resource_identifier"
    }
  ],
  "policy": {
    "latency_target_ms": 50,
    "min_path_redundancy": 2,
    "max_burst_cost_per_hr_eur": 200.0
  },
  "prices_eur": {
    "burst_capacity_per_1Gbps_hr": 15.0
  }
}
```

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'langgraph'`
- **Solution**: Ensure all dependencies are installed: `pip install -r requirements.txt`

**Issue**: Tests fail with import errors
- **Solution**: Run tests from project root: `cd /path/to/project && pytest tests/`

**Issue**: Artifacts directory not found
- **Solution**: The directory is created automatically on first use. Ensure write permissions.

**Issue**: API returns 404 for `/apply_option`
- **Solution**: Must call `/diagnose_issue` first to populate state store

## Development

### Project Principles
- **Separation of Concerns**: Each node handles one responsibility
- **Deterministic**: No randomness, reproducible outputs
- **Policy-First**: All recommendations must pass policy gates
- **Fail-Safe**: Errors captured and reported, never crash
- **Observable**: Detailed logging and artifact generation

### Contributing Guidelines
1. Follow existing code structure and naming conventions
2. Add tests for new features
3. Update documentation for API changes
4. Ensure all tests pass before committing
5. Use type hints for all function parameters

## License

Copyright 2025. All rights reserved.

## Contact & Support

For questions, issues, or contributions, please refer to the project repository.

