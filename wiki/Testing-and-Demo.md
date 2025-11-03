# Testing & Demo

Based on `DEMO_COPILOT.md`, tests, and README examples.

## Run Tests
```bash
python3 test_copilot.py
python3 test_langgraph_orchestrator.py
python3 test_production_enhancements.py
```

## Demo Script (Claude Desktop)
1) Start workflow with incident metrics
2) Approve diagnosis
3) Review recommendations (top 3)
4) Show commands for recommended playbook
5) Approve commands → execution + RCA

## Tips
- Use Option C (both MCP servers) for maximum flexibility
- Highlight safety: approvals, verification, rollback

