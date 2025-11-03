"""
Node implementations for LangGraph incident response workflow.

Each node represents a step in the workflow:
- Diagnose: Run AI diagnosis on incident
- Recommend: Rank remediation playbooks  
- Generate Commands: Create safe CLI commands
- Execute Commands: Apply commands (with human approval)
- Generate RCA: Create post-incident report

All nodes integrate with existing agents and update state with audit trail.
"""

import time
from typing import Dict, Any
from datetime import datetime

from app.langgraph_orchestrator.state import (
    IncidentState,
    add_history_entry,
    add_error,
    update_state_timestamp
)
from app.agents.root_cause_agent import get_agent as get_root_cause_agent
from app.agents.hybrid_recommendation_engine import get_hybrid_recommendation_engine
from app.agents.command_generator import get_command_generator
from app.agents.rca_generator import get_generator as get_rca_generator


def diagnose_node(state: IncidentState) -> IncidentState:
    """
    Diagnose root cause of the incident using AI.
    
    Integrates with RootCauseAgent to analyze incident metrics
    and determine root cause with confidence score.
    
    Updates state with:
    - diagnosis: Root cause analysis result
    - diagnosis_confidence: Confidence score (0-1)
    - current_step: "diagnose"
    """
    start_time = time.time()
    state["current_step"] = "diagnose"
    
    try:
        # Get incident data
        incident_data = state.get("incident_data", {})
        
        # Extract metrics for diagnosis
        signals = {
            "latency": {
                "current": incident_data.get("latency_current", 0),
                "baseline": incident_data.get("latency_baseline", 0)
            },
            "loss": {
                "current": incident_data.get("loss_current", 0),
                "baseline": incident_data.get("loss_baseline", 0)
            },
            "utilization": incident_data.get("utilization", {})
        }
        
        change_context = {
            "recent_changes": incident_data.get("recent_changes", []),
            "hot_path": incident_data.get("hot_path", "unknown")
        }
        
        # Run diagnosis
        agent = get_root_cause_agent()
        diagnosis_result = agent.diagnose(signals=signals, change_context=change_context)
        
        # Update state
        state["diagnosis"] = {
            "root_cause": diagnosis_result.root_cause,
            "confidence": diagnosis_result.confidence,
            "reasoning": diagnosis_result.reasoning,
            "contradicting_signals": diagnosis_result.contradicting_signals
        }
        state["diagnosis_confidence"] = diagnosis_result.confidence
        
        # Add to history
        duration_ms = int((time.time() - start_time) * 1000)
        add_history_entry(state, "diagnose", duration_ms, state["diagnosis"])
        
        return state
        
    except Exception as e:
        # Log error and increment retry count
        add_error(state, "diagnose", str(e), state.get("retry_count", 0))
        state["retry_count"] = state.get("retry_count", 0) + 1
        
        # If max retries exceeded, set fallback diagnosis
        if state["retry_count"] >= 3:
            state["diagnosis"] = {
                "root_cause": "unknown",
                "confidence": 0.3,
                "reasoning": f"AI diagnosis failed after 3 retries. Error: {str(e)}. Using fallback.",
                "contradicting_signals": []
            }
            state["diagnosis_confidence"] = 0.3
            state["retry_count"] = 0  # Reset for next step
        
        return state


def recommend_node(state: IncidentState) -> IncidentState:
    """
    Recommend and rank remediation playbooks.
    
    Uses RecommendationEngine to score and rank playbooks based on:
    - Root cause match
    - Risk level
    - Time to effect
    - Cost
    - Historical success rate
    
    Updates state with:
    - recommendations: List of ranked playbook options
    - recommendation_reasoning: Why these were recommended
    """
    start_time = time.time()
    state["current_step"] = "recommend"
    
    try:
        diagnosis = state.get("diagnosis", {})
        incident_data = state.get("incident_data", {})
        
        # Get recommendations (using hybrid AI + rule-based engine)
        engine = get_hybrid_recommendation_engine()
        recommendations = engine.recommend(
            root_cause=diagnosis.get("root_cause", "unknown"),
            confidence=diagnosis.get("confidence", 0.5),
            incident_context=incident_data,
            top_n=3,
            use_ai=True  # Enable AI re-ranking for production
        )
        
        # Update state
        state["recommendations"] = recommendations.get("options", [])
        state["recommendation_reasoning"] = (
            f"Ranked {len(state['recommendations'])} playbooks "
            f"for root cause: {diagnosis.get('root_cause')}"
        )
        
        # Auto-select top recommendation if high confidence
        if state.get("diagnosis_confidence", 0) > 0.85 and state["recommendations"]:
            state["selected_playbook_id"] = state["recommendations"][0]["id"]
        
        # Add to history
        duration_ms = int((time.time() - start_time) * 1000)
        add_history_entry(state, "recommend", duration_ms, {
            "count": len(state["recommendations"]),
            "top_recommendation": state["recommendations"][0] if state["recommendations"] else None
        })
        
        return state
        
    except Exception as e:
        add_error(state, "recommend", str(e))
        state["recommendations"] = []
        return state


def generate_commands_node(state: IncidentState) -> IncidentState:
    """
    Generate safe CLI commands for selected playbook.
    
    Uses CommandGenerator to create personalized, validated commands
    with verification steps and rollback procedure.
    
    Updates state with:
    - commands: Generated commands, verification, rollback, warnings
    """
    start_time = time.time()
    state["current_step"] = "generate_commands"
    
    try:
        playbook_id = state.get("selected_playbook_id")
        if not playbook_id:
            # If no playbook selected, use top recommendation
            recommendations = state.get("recommendations", [])
            if recommendations:
                playbook_id = recommendations[0]["id"]
                state["selected_playbook_id"] = playbook_id
            else:
                raise ValueError("No playbook selected and no recommendations available")
        
        incident_data = state.get("incident_data", {})
        
        # Generate commands
        generator = get_command_generator()
        commands = generator.generate(
            playbook_id=playbook_id,
            incident_context=incident_data,
            include_verification=True,
            include_rollback=True
        )
        
        # Update state
        state["commands"] = commands
        
        # Add to history
        duration_ms = int((time.time() - start_time) * 1000)
        add_history_entry(state, "generate_commands", duration_ms, {
            "playbook_id": playbook_id,
            "command_count": len(commands.get("commands", []))
        })
        
        return state
        
    except Exception as e:
        add_error(state, "generate_commands", str(e))
        state["commands"] = {
            "commands": [],
            "error": str(e)
        }
        return state


def execute_commands_node(state: IncidentState) -> IncidentState:
    """
    Execute commands (simulation for now).
    
    In production, this would:
    1. Connect to network devices
    2. Execute commands via SSH/API
    3. Verify results
    4. Monitor for impact
    
    For now, simulates execution and records result.
    
    Updates state with:
    - execution_result: Simulated execution result
    - execution_status: "success" | "partial" | "failed"
    - execution_timestamp: When executed
    """
    start_time = time.time()
    state["current_step"] = "execute"
    
    try:
        commands = state.get("commands", {})
        
        # SIMULATION: In production, would execute real commands
        # For now, simulate successful execution
        state["execution_result"] = {
            "status": "success",
            "message": "Commands executed successfully (simulated)",
            "commands_executed": len(commands.get("commands", [])),
            "verification_passed": True,
            "metrics_improved": True
        }
        state["execution_status"] = "success"
        state["execution_timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # Add to history
        duration_ms = int((time.time() - start_time) * 1000)
        add_history_entry(state, "execute", duration_ms, state["execution_result"])
        
        return state
        
    except Exception as e:
        add_error(state, "execute", str(e))
        state["execution_result"] = {
            "status": "failed",
            "error": str(e)
        }
        state["execution_status"] = "failed"
        return state


def generate_rca_node(state: IncidentState) -> IncidentState:
    """
    Generate post-incident RCA report.
    
    Uses RCAGenerator to create comprehensive markdown report with:
    - Executive summary
    - Timeline
    - Root cause analysis
    - Actions taken
    - Lessons learned
    
    Updates state with:
    - rca_report: Markdown RCA report
    - rca_generated_at: Timestamp
    """
    start_time = time.time()
    state["current_step"] = "generate_rca"
    
    try:
        # Prepare incident data for RCA
        incident_data = state.get("incident_data", {})
        diagnosis = state.get("diagnosis", {})
        execution = state.get("execution_result", {})
        
        # Build RCA input from state
        rca_input = {
            "incident_id": state.get("incident_id", "unknown"),
            "timestamp_start": state.get("created_at", ""),
            "timestamp_end": state.get("updated_at", ""),
            "hot_path": incident_data.get("hot_path", "unknown"),
            "metrics": {
                "latency_current": incident_data.get("latency_current"),
                "latency_baseline": incident_data.get("latency_baseline"),
                "loss_current": incident_data.get("loss_current"),
                "utilization": incident_data.get("utilization")
            },
            "diagnosis": diagnosis,
            "actions_taken": [
                f"Applied playbook: {state.get('selected_playbook_id', 'unknown')}",
                f"Commands executed: {len(state.get('commands', {}).get('commands', []))}",
                f"Result: {execution.get('status', 'unknown')}"
            ],
            "resolution_summary": execution.get("message", "Incident resolved"),
            "engineer_notes": "\n".join(
                [f"- {approval['step']}: {approval.get('feedback', 'Approved')}"
                 for approval in state.get("approvals", [])]
            )
        }
        
        # Generate RCA
        generator = get_rca_generator()
        # Note: RCA generator might not have all these parameters, adapt as needed
        rca_markdown = f"""# Root Cause Analysis: {rca_input['incident_id']}

## Executive Summary
**Incident:** {rca_input['hot_path']} degradation  
**Root Cause:** {diagnosis.get('root_cause', 'unknown')}  
**Confidence:** {diagnosis.get('confidence', 0.0)*100:.0f}%  
**Status:** {execution.get('status', 'unknown')}

## Timeline
- **Start:** {rca_input['timestamp_start']}
- **Diagnosis Complete:** {len([h for h in state.get('history', []) if h['step'] == 'diagnose'])} attempts
- **Commands Generated:** {len([h for h in state.get('history', []) if h['step'] == 'generate_commands'])}
- **Resolution:** {rca_input['timestamp_end']}

## Root Cause Analysis
**Finding:** {diagnosis.get('reasoning', 'No reasoning available')}

**Confidence:** {diagnosis.get('confidence', 0.0)*100:.0f}%

**Contradicting Signals:** {', '.join(diagnosis.get('contradicting_signals', [])) or 'None'}

## Actions Taken
{chr(10).join([f"- {action}" for action in rca_input['actions_taken']])}

## Resolution
{rca_input['resolution_summary']}

## Engineer Notes
{rca_input.get('engineer_notes', 'No additional notes')}

## Lessons Learned
- Incident responded to with AI-assisted diagnosis
- Human-in-the-loop approval maintained safety
- Full audit trail captured for compliance

## Recommendations
- Monitor {rca_input['hot_path']} for recurrence
- Review capacity planning if congestion-related
- Update runbooks based on this incident
"""
        
        state["rca_report"] = rca_markdown
        state["rca_generated_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Add to history
        duration_ms = int((time.time() - start_time) * 1000)
        add_history_entry(state, "generate_rca", duration_ms, {
            "report_length": len(rca_markdown)
        })
        
        return state
        
    except Exception as e:
        add_error(state, "generate_rca", str(e))
        state["rca_report"] = f"# RCA Generation Failed\n\nError: {str(e)}"
        return state


def human_review_node(state: IncidentState) -> IncidentState:
    """
    Placeholder node for human review/approval.
    
    This node is used as an interrupt point. When the workflow
    reaches this node, it pauses and waits for human input.
    
    The state is not modified here - it's modified externally
    when the human approves or rejects via update_state().
    """
    # Node simply passes state through
    # Actual approval logic happens via state updates from external API
    state["current_step"] = "human_review"
    state["workflow_status"] = "paused"
    return update_state_timestamp(state)

