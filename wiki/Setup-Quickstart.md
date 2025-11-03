# Setup & Quickstart

Summarizes `QUICK_START.md`, `QUICKSTART.md`, and README run instructions.

## Install
```bash
pip install -r requirements.txt
```

## Run API
```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Open http://localhost:8000/docs
```

## Minimal Workflow (API)
```bash
curl -X POST http://localhost:8000/api/workflows/start \
  -H "Content-Type: application/json" \
  -d '{
    "incident_id": "INC-001",
    "hot_path": "RouterB-RouterC",
    "latency_current": 125.0,
    "loss_current": 2.1,
    "priority": "high"
  }'
```

## Tests
```bash
python3 test_copilot.py
python3 test_langgraph_orchestrator.py
python3 test_production_enhancements.py
```

Next: [MCP Setup](MCP-Setup.md), [MCP Tools](MCP-Tools.md).

