# Quick Start Guide

## Installation (30 seconds)

```bash
cd Agentic-Networks-Incident-Copilot
pip install -r requirements.txt
```

## Start the Server (5 seconds)

```bash
python3 -m uvicorn app.main:app --reload
```

Server will be running at: `http://127.0.0.1:8000` or `http://localhost:8000`

## Run the Demo (30 seconds)

In a new terminal:

```bash
python demo.py
```

This will:
1. ✅ Check if the API is running
2. 🔍 Diagnose sample incidents
3. 📋 Show remediation options
4. ⚡ Apply recommendations
5. 📊 Generate artifacts (charts + reports)

## View Results

Open the generated one-pager:
```bash
open artifacts/INC-20250101-001/summary.html
```

## Interactive API Testing

Visit the FastAPI interactive docs:
```
http://localhost:8000/docs
```

## Manual API Testing

### 1. Diagnose an Incident

```bash
curl -X POST http://localhost:8000/diagnose_issue \
  -H "Content-Type: application/json" \
  -d @tests/test_incident_basic.json
```

### 2. Apply Remediation

```bash
curl -X POST http://localhost:8000/apply_option \
  -H "Content-Type: application/json" \
  -d '{
    "incident_id": "INC-20250101-001",
    "option_id": "opt_partial_offload_40"
  }'
```

## Run Tests

```bash
pytest tests/ -v
```

## What's Next?

- ✏️ Modify test incidents in `tests/` directory
- 🎯 Add new playbooks in `app/playbooks.py`
- 📚 Extend runbook corpus in `app/runbooks/`
- 🔧 Customize nodes in `app/nodes/`
- 📖 Read full documentation in `README.md`

## Troubleshooting

**Server won't start?**
- Ensure Python 3.12+ is installed
- Check port 8000 is available

**Tests failing?**
- Run from project root directory
- Verify all dependencies installed

**Artifacts not generating?**
- Check write permissions on `artifacts/` directory
- Ensure matplotlib backend is configured

## Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI endpoints |
| `app/graph.py` | LangGraph orchestration |
| `app/models.py` | Data models |
| `app/nodes/` | Workflow nodes |
| `tests/*.json` | Sample incidents |
| `demo.py` | Interactive demo |

---

**Total Setup Time**: ~2 minutes  
**First Demo Run**: ~30 seconds  
**You're ready to go!** 🚀

