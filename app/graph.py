"""
LangGraph orchestration for incident analysis workflow.
"""

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from app.models import IncidentState
from app.nodes.ingest_bundle import ingest_bundle
from app.nodes.score_signals import score_signals
from app.nodes.correlate_changes import correlate_changes
from app.nodes.hypothesize_root_cause import hypothesize_root_cause
from app.nodes.rank_playbooks import rank_playbooks
from app.nodes.justify_with_runbooks import justify_with_runbooks
from app.nodes.policy_gate import policy_gate
from app.nodes.synthesize_plan import synthesize_plan
from app.nodes.apply_stub_and_project import apply_stub_and_project
from app.nodes.deliver_artifacts import deliver_artifacts


def should_skip_to_artifacts(state: dict) -> str:
    """
    Conditional edge: check if we should skip to artifacts due to error.
    """
    if state.get("error"):
        return "deliver_artifacts"
    return "continue"


def should_skip_plan(state: dict) -> str:
    """
    Conditional edge: check if we should skip plan synthesis.
    """
    if state.get("error") or not state.get("recommendation"):
        return "deliver_artifacts"
    return "synthesize_plan"


def build_graph(include_justification: bool = False):
    """
    Build and compile the LangGraph workflow.
    
    Args:
        include_justification: Whether to include the optional justify_with_runbooks node
        
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the state graph
    workflow = StateGraph(IncidentState)
    
    # Add all nodes
    workflow.add_node("ingest_bundle", ingest_bundle)
    workflow.add_node("score_signals", score_signals)
    workflow.add_node("correlate_changes", correlate_changes)
    workflow.add_node("hypothesize_root_cause", hypothesize_root_cause)
    workflow.add_node("rank_playbooks", rank_playbooks)
    
    if include_justification:
        workflow.add_node("justify_with_runbooks", justify_with_runbooks)
    
    workflow.add_node("policy_gate", policy_gate)
    workflow.add_node("synthesize_plan", synthesize_plan)
    workflow.add_node("apply_stub_and_project", apply_stub_and_project)
    workflow.add_node("deliver_artifacts", deliver_artifacts)
    
    # Set entry point
    workflow.set_entry_point("ingest_bundle")
    
    # Add edges for the main flow
    workflow.add_edge("ingest_bundle", "score_signals")
    workflow.add_edge("score_signals", "correlate_changes")
    workflow.add_edge("correlate_changes", "hypothesize_root_cause")
    workflow.add_edge("hypothesize_root_cause", "rank_playbooks")
    
    # Optional justification step
    if include_justification:
        workflow.add_edge("rank_playbooks", "justify_with_runbooks")
        workflow.add_edge("justify_with_runbooks", "policy_gate")
    else:
        workflow.add_edge("rank_playbooks", "policy_gate")
    
    # After policy gate, decide whether to synthesize plan
    workflow.add_conditional_edges(
        "policy_gate",
        should_skip_plan,
        {
            "synthesize_plan": "synthesize_plan",
            "deliver_artifacts": "deliver_artifacts"
        }
    )
    
    workflow.add_edge("synthesize_plan", "apply_stub_and_project")
    workflow.add_edge("apply_stub_and_project", "deliver_artifacts")
    workflow.add_edge("deliver_artifacts", END)
    
    # Compile the graph
    app = workflow.compile()
    
    return app


def run_graph_until(graph, state: IncidentState, stop_at: str = None):
    """
    Run the graph until a specific node.
    
    Args:
        graph: Compiled LangGraph
        state: Initial state
        stop_at: Node name to stop at (None = run to completion)
        
    Returns:
        Final state
    """
    if stop_at:
        # For stopping at a specific node, we need to manually execute nodes
        current_state = state
        node_sequence = [
            "ingest_bundle",
            "score_signals", 
            "correlate_changes",
            "hypothesize_root_cause",
            "rank_playbooks",
            "policy_gate",
            "synthesize_plan",
            "apply_stub_and_project",
            "deliver_artifacts"
        ]
        
        for node_name in node_sequence:
            if node_name == "ingest_bundle":
                current_state = ingest_bundle(current_state)
            elif node_name == "score_signals":
                current_state = score_signals(current_state)
            elif node_name == "correlate_changes":
                current_state = correlate_changes(current_state)
            elif node_name == "hypothesize_root_cause":
                current_state = hypothesize_root_cause(current_state)
            elif node_name == "rank_playbooks":
                current_state = rank_playbooks(current_state)
            elif node_name == "policy_gate":
                current_state = policy_gate(current_state)
            
            if node_name == stop_at:
                break
            
            # Stop early if error
            if current_state.error:
                break
        
        return current_state
    else:
        # Run to completion
        result = graph.invoke(state)
        return result


def run_graph_from(graph, state: IncidentState, start_from: str):
    """
    Run the graph starting from a specific node.
    
    Args:
        graph: Compiled LangGraph
        state: Initial state
        start_from: Node name to start from
        
    Returns:
        Final state
    """
    current_state = state
    node_sequence = [
        "synthesize_plan",
        "apply_stub_and_project",
        "deliver_artifacts"
    ]
    
    start_index = node_sequence.index(start_from) if start_from in node_sequence else 0
    
    for node_name in node_sequence[start_index:]:
        if node_name == "synthesize_plan":
            current_state = synthesize_plan(current_state)
        elif node_name == "apply_stub_and_project":
            current_state = apply_stub_and_project(current_state)
        elif node_name == "deliver_artifacts":
            current_state = deliver_artifacts(current_state)
        
        if current_state.error:
            break
    
    return current_state

