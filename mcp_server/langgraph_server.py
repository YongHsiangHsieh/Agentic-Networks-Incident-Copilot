"""
Production MCP server with LangGraph workflow integration.

Exposes LangGraph workflow tools to Claude Desktop for:
- Starting incident workflows
- Checking workflow status
- Approving/rejecting at checkpoints
- Viewing history and audit trail

This enables human-in-the-loop workflow management via natural language conversation.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

from app.langgraph_orchestrator.graph import get_workflow_instance
from app.langgraph_orchestrator.state import create_initial_state


# Initialize MCP server
mcp_server = Server("network-copilot-langgraph")


@mcp_server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available workflow management tools."""
    return [
        types.Tool(
            name="start_incident_workflow",
            description=(
                "Start a new incident response workflow with human-in-the-loop approval gates. "
                "This initiates the workflow and runs diagnosis. Engineer must approve before continuing. "
                "Use when a new network incident is detected."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "string",
                        "description": "Unique incident identifier (e.g., 'INC-2024-11-02-001')"
                    },
                    "hot_path": {
                        "type": "string",
                        "description": "Affected network path (e.g., 'RouterB-RouterC')"
                    },
                    "latency_current": {
                        "type": "number",
                        "description": "Current latency in milliseconds"
                    },
                    "loss_current": {
                        "type": "number",
                        "description": "Current packet loss percentage"
                    },
                    "latency_baseline": {
                        "type": "number",
                        "description": "Baseline latency (optional, will estimate if not provided)"
                    },
                    "loss_baseline": {
                        "type": "number",
                        "description": "Baseline packet loss (optional)"
                    },
                    "utilization": {
                        "type": "object",
                        "description": "Utilization by segment (optional)"
                    },
                    "priority": {
                        "type": "string",
                        "description": "Incident priority: low/medium/high/critical",
                        "enum": ["low", "medium", "high", "critical"]
                    }
                },
                "required": ["incident_id", "hot_path", "latency_current", "loss_current"]
            }
        ),
        
        types.Tool(
            name="get_workflow_status",
            description=(
                "Check the current status of an incident workflow. "
                "Shows current step, diagnosis results, pending approvals, and history. "
                "Use to check progress or see what needs approval."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "string",
                        "description": "Incident identifier"
                    }
                },
                "required": ["incident_id"]
            }
        ),
        
        types.Tool(
            name="approve_diagnosis",
            description=(
                "Approve or reject the AI diagnosis and resume workflow. "
                "If approved, continues to recommendations and command generation. "
                "If rejected, workflow stops (can restart with new parameters). "
                "Use after reviewing diagnosis results."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "string",
                        "description": "Incident identifier"
                    },
                    "approved": {
                        "type": "boolean",
                        "description": "True to approve, False to reject"
                    },
                    "feedback": {
                        "type": "string",
                        "description": "Engineer's feedback or comments (optional)"
                    },
                    "approved_by": {
                        "type": "string",
                        "description": "Engineer email (optional)"
                    }
                },
                "required": ["incident_id", "approved"]
            }
        ),
        
        types.Tool(
            name="approve_commands",
            description=(
                "Approve or reject generated commands and complete workflow. "
                "If approved, executes commands (simulated) and generates RCA. "
                "If rejected, workflow stops. This is the final safety checkpoint. "
                "Use after reviewing commands for safety."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "string",
                        "description": "Incident identifier"
                    },
                    "approved": {
                        "type": "boolean",
                        "description": "True to approve, False to reject"
                    },
                    "feedback": {
                        "type": "string",
                        "description": "Engineer's feedback or comments (optional)"
                    },
                    "approved_by": {
                        "type": "string",
                        "description": "Engineer email (optional)"
                    }
                },
                "required": ["incident_id", "approved"]
            }
        ),
        
        types.Tool(
            name="get_workflow_history",
            description=(
                "Get complete workflow history and audit trail for an incident. "
                "Shows all steps executed, approvals given, and errors encountered. "
                "Use for compliance audits, debugging, or post-incident review."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "string",
                        "description": "Incident identifier"
                    }
                },
                "required": ["incident_id"]
            }
        ),
        
        types.Tool(
            name="select_playbook",
            description=(
                "Manually select a specific remediation playbook (override AI recommendation). "
                "Use when engineer wants a different approach than AI recommended. "
                "Call after seeing recommendations but before approving commands."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "string",
                        "description": "Incident identifier"
                    },
                    "playbook_id": {
                        "type": "string",
                        "description": "Playbook ID (e.g., 'qos_traffic_shaping', 'config_rollback')"
                    }
                },
                "required": ["incident_id", "playbook_id"]
            }
        )
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls from Claude."""
    
    try:
        if name == "start_incident_workflow":
            result = start_incident_workflow(arguments)
        elif name == "get_workflow_status":
            result = get_workflow_status(arguments)
        elif name == "approve_diagnosis":
            result = approve_diagnosis(arguments)
        elif name == "approve_commands":
            result = approve_commands(arguments)
        elif name == "get_workflow_history":
            result = get_workflow_history(arguments)
        elif name == "select_playbook":
            result = select_playbook(arguments)
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        # Format response
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": str(e)}, indent=2)
        )]


def start_incident_workflow(args: dict) -> dict:
    """Start a new incident workflow."""
    incident_id = args["incident_id"]
    
    # Create initial state
    initial_state = create_initial_state(
        incident_id=incident_id,
        incident_data={
            "hot_path": args["hot_path"],
            "latency_current": args["latency_current"],
            "latency_baseline": args.get("latency_baseline", args["latency_current"] * 0.5),
            "loss_current": args["loss_current"],
            "loss_baseline": args.get("loss_baseline", 0.1),
            "utilization": args.get("utilization", {}),
            "recent_changes": [],
            "priority": args.get("priority", "medium")
        },
        priority=args.get("priority", "medium")
    )
    
    # Get workflow and start
    app = get_workflow_instance()
    result = app.invoke(
        initial_state,
        config={"configurable": {"thread_id": incident_id}}
    )
    
    # Format response for engineer
    diagnosis = result.get("diagnosis", {})
    
    return {
        "status": "workflow_started",
        "message": f"Workflow started for {incident_id}. Diagnosis complete, waiting for approval.",
        "incident_id": incident_id,
        "current_step": result.get("current_step"),
        "diagnosis": {
            "root_cause": diagnosis.get("root_cause"),
            "confidence": f"{diagnosis.get('confidence', 0)*100:.0f}%",
            "reasoning": diagnosis.get("reasoning"),
            "contradicting_signals": diagnosis.get("contradicting_signals", [])
        },
        "next_action": "Review diagnosis above. Call approve_diagnosis to continue or reject to stop."
    }


def get_workflow_status(args: dict) -> dict:
    """Get current workflow status."""
    incident_id = args["incident_id"]
    
    app = get_workflow_instance()
    state = app.get_state(config={"configurable": {"thread_id": incident_id}})
    
    if not state or not state.values:
        return {"error": f"Workflow not found for {incident_id}"}
    
    values = state.values
    
    # Determine what's pending
    pending = []
    if not values.get("diagnosis_approved"):
        pending.append("diagnosis approval")
    if values.get("diagnosis_approved") and not values.get("commands_approved"):
        pending.append("commands approval")
    
    return {
        "incident_id": incident_id,
        "current_step": values.get("current_step"),
        "workflow_status": values.get("workflow_status"),
        "pending_approvals": pending,
        "diagnosis": values.get("diagnosis"),
        "recommendations": values.get("recommendations", [])[:3],  # Top 3
        "commands_count": len(values.get("commands", {}).get("commands", [])),
        "history_steps": len(values.get("history", [])),
        "approvals_given": len(values.get("approvals", [])),
        "errors": len(values.get("errors", []))
    }


def approve_diagnosis(args: dict) -> dict:
    """Approve or reject diagnosis."""
    incident_id = args["incident_id"]
    approved = args["approved"]
    
    app = get_workflow_instance()
    config = {"configurable": {"thread_id": incident_id}}
    
    # Update state with approval
    app.update_state(
        config=config,
        values={
            "diagnosis_approved": approved,
            "diagnosis_feedback": args.get("feedback", ""),
        }
    )
    
    if not approved:
        return {
            "status": "diagnosis_rejected",
            "message": "Diagnosis rejected. Workflow stopped.",
            "incident_id": incident_id,
            "feedback": args.get("feedback")
        }
    
    # Resume workflow (runs until next checkpoint)
    result = app.invoke(None, config=config)
    
    recommendations = result.get("recommendations", [])
    commands = result.get("commands", {})
    
    return {
        "status": "diagnosis_approved",
        "message": "Diagnosis approved. Recommendations generated and commands ready for review.",
        "incident_id": incident_id,
        "recommendations": [
            {
                "rank": i+1,
                "name": rec.get("name"),
                "id": rec.get("id"),
                "risk": rec.get("risk_level"),
                "time": rec.get("time_to_effect"),
                "success_rate": rec.get("success_rate"),
                "reasoning": rec.get("reasoning", rec.get("ai_reasoning", ""))[:150] + "..."
            }
            for i, rec in enumerate(recommendations[:3])
        ],
        "commands": {
            "count": len(commands.get("commands", [])),
            "playbook": result.get("selected_playbook_id"),
            "preview": commands.get("commands", [])[:2] if commands.get("commands") else []
        },
        "next_action": "Review commands above. Call approve_commands to execute or reject to stop."
    }


def approve_commands(args: dict) -> dict:
    """Approve or reject commands."""
    incident_id = args["incident_id"]
    approved = args["approved"]
    
    app = get_workflow_instance()
    config = {"configurable": {"thread_id": incident_id}}
    
    # Get current approvals to append
    state = app.get_state(config=config)
    current_approvals = state.values.get("approvals", [])
    
    # Add new approval
    new_approval = {
        "step": "commands",
        "approved": approved,
        "approved_by": args.get("approved_by"),
        "feedback": args.get("feedback"),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Update state
    app.update_state(
        config=config,
        values={
            "commands_approved": approved,
            "commands_feedback": args.get("feedback", ""),
            "approvals": current_approvals + [new_approval]
        }
    )
    
    if not approved:
        return {
            "status": "commands_rejected",
            "message": "Commands rejected. Workflow stopped.",
            "incident_id": incident_id,
            "feedback": args.get("feedback")
        }
    
    # Resume workflow (completes execution and RCA)
    result = app.invoke(None, config=config)
    
    execution = result.get("execution_result", {})
    rca = result.get("rca_report", "")
    
    return {
        "status": "workflow_complete",
        "message": "Commands approved and executed. RCA report generated.",
        "incident_id": incident_id,
        "execution": {
            "status": execution.get("status"),
            "message": execution.get("message")
        },
        "rca_preview": rca[:500] + "..." if len(rca) > 500 else rca,
        "rca_length": len(rca),
        "next_action": "Workflow complete. Review RCA report for documentation."
    }


def get_workflow_history(args: dict) -> dict:
    """Get complete workflow history."""
    incident_id = args["incident_id"]
    
    app = get_workflow_instance()
    state = app.get_state(config={"configurable": {"thread_id": incident_id}})
    
    if not state or not state.values:
        return {"error": f"Workflow not found for {incident_id}"}
    
    values = state.values
    
    return {
        "incident_id": incident_id,
        "created_at": values.get("created_at"),
        "updated_at": values.get("updated_at"),
        "priority": values.get("priority"),
        "workflow_steps": [
            {
                "step": h.get("step"),
                "timestamp": h.get("timestamp"),
                "duration_ms": h.get("duration_ms")
            }
            for h in values.get("history", [])
        ],
        "approvals": values.get("approvals", []),
        "errors": values.get("errors", []),
        "final_state": {
            "diagnosis": values.get("diagnosis"),
            "execution_status": values.get("execution_status"),
            "rca_generated": bool(values.get("rca_report"))
        }
    }


def select_playbook(args: dict) -> dict:
    """Manually select a playbook."""
    incident_id = args["incident_id"]
    playbook_id = args["playbook_id"]
    
    app = get_workflow_instance()
    config = {"configurable": {"thread_id": incident_id}}
    
    # Update state
    app.update_state(
        config=config,
        values={"selected_playbook_id": playbook_id}
    )
    
    return {
        "status": "playbook_selected",
        "message": f"Manually selected playbook: {playbook_id}",
        "incident_id": incident_id,
        "selected_playbook": playbook_id,
        "next_action": "Commands will be regenerated for this playbook. Review and approve."
    }


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

