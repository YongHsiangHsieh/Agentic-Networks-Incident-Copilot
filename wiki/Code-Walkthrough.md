# Code Walkthrough

This page distills `CODE_WALKTHROUGH.md` with file-oriented guidance.

## Request Flow
- MCP/REST → `app/copilot/orchestrator.py` → agents
- Structured inputs/outputs via Pydantic models in `app/models.py`

## Key Files
- `app/agents/root_cause_agent.py`: AI diagnosis with structured prompts + fallback
- `app/agents/recommendation_engine.py`: multi-factor scoring
- `app/agents/hybrid_recommendation_engine.py`: rule pre-filter + AI re-rank
- `app/agents/command_generator.py`: safe templates, verification, rollback
- `app/agents/rca_generator.py`: RCA narratives using context + reuse diagnosis
- `app/langgraph_orchestrator/*`: state, nodes, routing, compiled app
- `app/api/workflow_endpoints.py`: production REST workflow
- `mcp_server/*`: MCP servers (direct and LangGraph)

## Patterns
- Singleton `get_*()` helpers for agents
- Try/except with rule fallback for reliability
- Natural-language context building for LLMs
- Pydantic schemas for validation and automation

## Tracing a Call
1) Diagnose: orchestrator builds signals, Root Cause Agent analyzes
2) Recommend: rule score → optional AI re-rank
3) Commands: render playbook template with validated params
4) RCA: reuse diagnosis + metrics to produce markdown

See also: [Architecture](Architecture.md), [LangGraph Workflow](LangGraph-Workflow.md).

