"""
LangGraph-based orchestrator for production-ready incident response workflows.

Provides:
- Human-in-the-loop approval gates
- State persistence and resumability
- Error recovery with retries
- Full audit trail
- Conditional routing based on confidence
"""

from app.langgraph_orchestrator.graph import get_incident_workflow

__all__ = ["get_incident_workflow"]

