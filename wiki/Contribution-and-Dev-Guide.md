# Contribution & Development Guide

Guidance distilled from docs and codebase for day-to-day development.

## Local Dev
- Create virtualenv; `pip install -r requirements.txt`
- Run tests regularly (see [Testing & Demo](Testing-and-Demo.md))

## Coding Standards
- Prefer explicit types; use Pydantic models at boundaries
- Keep prompts structured and include validation steps
- Add safety checks for any new command templates
- Maintain single-responsibility modules (new agent = new file)

## Extending the System
- Add playbooks in `app/playbooks/playbook_library.py`
- Tune scoring in `recommendation_engine.py`; add AI re-rank features in `hybrid_recommendation_engine.py`
- Add MCP tools in `mcp_server/*` mirroring REST endpoints
- Add LangGraph nodes and routes in `app/langgraph_orchestrator/*`

## Documentation
- Update Wiki pages when adding features
- Keep `README.md` and this Wiki index aligned

