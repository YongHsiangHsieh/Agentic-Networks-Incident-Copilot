"""
LangGraph-based incident response workflow graph.

This defines the complete production-ready workflow with:
- Human-in-the-loop approval gates
- State persistence via checkpointing
- Conditional routing based on approvals
- Error recovery with retries
- Full audit trail

Workflow:
1. Diagnose → 2. Human Review → 3. Recommend → 4. Generate Commands →
5. Human Review → 6. Execute → 7. Generate RCA → END

With interrupt points at steps 2 and 5 for human approval.
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.langgraph_orchestrator.state import IncidentState
from app.langgraph_orchestrator.nodes import (
    diagnose_node,
    recommend_node,
    generate_commands_node,
    execute_commands_node,
    generate_rca_node,
    human_review_node
)
from app.langgraph_orchestrator.routing import (
    route_after_diagnosis_review,
    route_after_commands_review,
    route_after_execution
)


def build_incident_workflow_graph() -> StateGraph:
    """
    Build the complete incident response workflow graph.
    
    Returns:
        StateGraph configured with all nodes, edges, and routing logic
    """
    # Create graph with IncidentState
    workflow = StateGraph(IncidentState)
    
    # ===== ADD NODES =====
    
    # Core workflow nodes
    workflow.add_node("diagnose", diagnose_node)
    workflow.add_node("recommend", recommend_node)
    workflow.add_node("generate_commands", generate_commands_node)
    workflow.add_node("execute", execute_commands_node)
    workflow.add_node("generate_rca", generate_rca_node)
    
    # Human-in-the-loop review nodes (interrupt points)
    workflow.add_node("review_diagnosis", human_review_node)
    workflow.add_node("review_commands", human_review_node)
    
    # ===== SET ENTRY POINT =====
    workflow.set_entry_point("diagnose")
    
    # ===== ADD EDGES =====
    
    # After diagnosis → human review
    workflow.add_edge("diagnose", "review_diagnosis")
    
    # After diagnosis review → conditional routing
    workflow.add_conditional_edges(
        "review_diagnosis",
        route_after_diagnosis_review,
        {
            "approved": "recommend",  # Approved → continue to recommendations
            "retry": "diagnose",      # Not satisfied → re-diagnose
            "stop": END              # Reject → end workflow
        }
    )
    
    # After recommendations → generate commands
    workflow.add_edge("recommend", "generate_commands")
    
    # After command generation → human review
    workflow.add_edge("generate_commands", "review_commands")
    
    # After commands review → conditional routing
    workflow.add_conditional_edges(
        "review_commands",
        route_after_commands_review,
        {
            "execute": "execute",           # Approved → execute commands
            "modify": "generate_commands",  # Needs changes → regenerate
            "stop": END                     # Reject → end workflow
        }
    )
    
    # After execution → conditional routing
    workflow.add_conditional_edges(
        "execute",
        route_after_execution,
        {
            "rca": "generate_rca",  # Success → generate RCA
            "retry": "execute",     # Failed → retry execution
            "stop": END             # Fatal error → end
        }
    )
    
    # After RCA generation → end workflow
    workflow.add_edge("generate_rca", END)
    
    return workflow


def get_incident_workflow(checkpointer=None):
    """
    Get compiled incident workflow with optional custom checkpointer.
    
    Args:
        checkpointer: Optional checkpointer for state persistence.
                     Defaults to MemorySaver for in-memory persistence.
    
    Returns:
        Compiled workflow app ready for execution
    
    Usage:
        # Create workflow
        app = get_incident_workflow()
        
        # Start incident workflow
        result = app.invoke(
            initial_state,
            config={"configurable": {"thread_id": "INC-001"}}
        )
        # → Pauses at first human review
        
        # Human approves diagnosis
        app.update_state(
            config={"configurable": {"thread_id": "INC-001"}},
            values={"diagnosis_approved": True}
        )
        
        # Resume workflow
        result = app.invoke(
            None,
            config={"configurable": {"thread_id": "INC-001"}}
        )
        # → Continues from checkpoint, pauses at second review
        
        # Human approves commands
        app.update_state(
            config={"configurable": {"thread_id": "INC-001"}},
            values={"commands_approved": True}
        )
        
        # Resume to completion
        result = app.invoke(
            None,
            config={"configurable": {"thread_id": "INC-001"}}
        )
        # → Completes workflow, returns final state
    """
    # Build graph
    graph = build_incident_workflow_graph()
    
    # Use provided checkpointer or default to in-memory
    if checkpointer is None:
        checkpointer = MemorySaver()
    
    # Compile with checkpointer and interrupt points
    app = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["review_diagnosis", "review_commands"]
    )
    
    return app


# Singleton instance for easy access
_workflow_instance = None


def get_workflow_instance():
    """
    Get singleton workflow instance.
    
    This ensures we reuse the same compiled workflow and checkpointer
    across requests, maintaining state persistence.
    """
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = get_incident_workflow()
    return _workflow_instance

