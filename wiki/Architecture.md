# Architecture

This page consolidates the WHY and high-level design from `ARCHITECTURE_DEEP_DIVE.md`, `MCP_LANGGRAPH_ARCHITECTURE.md`, and `LANGGRAPH_IMPLEMENTATION_COMPLETE.md`.

## Problem & Solution
- Incidents are high-stakes and socio-technical; full automation is risky.
- Copilot approach: AI assists; humans approve at critical gates.

## System Overview
```
Interfaces → REST API / MCP
                 │
                 ▼
          LangGraph Orchestrator
  diagnose → recommend → commands → execute → rca
                 ▲             │
           human approvals ────┘
```

- Agents: Root Cause, Recommendation (hybrid), Command Generator, RCA Generator
- State: `IncidentState` persists data, approvals, history, errors, and metadata
- Playbooks: Structured remediation procedures with risk, time, cost, and success rates

## Design Principles
- Safety over speed; explicit human approvals
- Hybrid recommendations; fallback to rules if AI unavailable
- Durable workflows with audit trail
- Open interfaces (REST + MCP)

## Key Trade-offs
- AI + rule fallback; multi-agent vs monolith; structured outputs vs free text; post-incident RCA focus vs real-time autonomy.

## Data Flow (Simplified)
1) Orchestrator receives incident context
2) Root Cause Agent analyzes signals (utilization-first), validates contradictions
3) Recommendation Engine pre-filters and scores; AI re-ranks top candidates
4) Command Generator renders validated templates with verification + rollback
5) Human approvals at diagnosis and command checkpoints
6) Execute (simulated) and generate RCA

## LangGraph Workflow
- Nodes: `diagnose`, `review_diagnosis`, `recommend`, `generate_commands`, `review_commands`, `execute`, `generate_rca`
- Conditional routing via `routing.py`
- Checkpointing with `MemorySaver`; interrupt at human review nodes

## AI Strategy (AWS Bedrock)
- Default model: Claude Haiku (fast, low-cost); upgrade to Sonnet for deeper reasoning as needed
- Pydantic-validated structured outputs
- Context building in natural language for LLMs; explicit validation steps

## Security & Safety
- MCP runs locally; no auto-execution of device commands
- Approvals recorded with timestamps and approvers
- Safety warnings and rollback embedded in command outputs

## Future
- Persistent checkpoint store (Postgres/Redis)
- Real-time telemetry ingestion and mid-run enrichment
- Optional execution adapters with stronger safety

See also: [LangGraph Workflow](LangGraph-Workflow.md), [Agents](Agents.md), [Production Enhancements](Production-Enhancements.md).

