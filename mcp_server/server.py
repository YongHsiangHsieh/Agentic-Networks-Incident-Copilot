#!/usr/bin/env python3
"""
MCP Server for Network Incident Copilot.

Exposes four core tools for Claude Desktop integration:
1. diagnose_incident - Analyze incident and identify root cause
2. recommend_actions - Suggest ranked remediation options
3. show_commands - Generate safe CLI commands
4. generate_rca - Create comprehensive RCA report
"""

import asyncio
import json
import logging
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from app.copilot.orchestrator import get_copilot
from app.models import IncidentData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("network-copilot-mcp")

# Initialize server
server = Server("network-copilot")
copilot = get_copilot()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools"""
    return [
        Tool(
            name="diagnose_incident",
            description=(
                "Analyze a network incident and identify the root cause. "
                "Provides diagnosis with confidence level, evidence, and severity assessment. "
                "Use this as the first step when investigating any network issue."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "hot_path": {
                        "type": "string",
                        "description": "Affected network path (e.g., 'RouterB-RouterC')"
                    },
                    "latency_current": {
                        "type": "number",
                        "description": "Current latency in milliseconds"
                    },
                    "latency_baseline": {
                        "type": "number",
                        "description": "Baseline/normal latency in milliseconds"
                    },
                    "loss_current": {
                        "type": "number",
                        "description": "Current packet loss percentage"
                    },
                    "loss_baseline": {
                        "type": "number",
                        "description": "Baseline/normal packet loss percentage"
                    },
                    "utilization": {
                        "type": "object",
                        "description": "Utilization percentages by segment (e.g., {'RouterB-RouterC': 78.5})",
                        "additionalProperties": {"type": "number"}
                    },
                    "recent_changes": {
                        "type": "array",
                        "description": "Recent configuration changes or actions taken",
                        "items": {"type": "string"}
                    }
                },
                "required": ["hot_path", "latency_current", "loss_current"]
            }
        ),
        Tool(
            name="recommend_actions",
            description=(
                "Get ranked remediation recommendations based on incident diagnosis. "
                "Returns 3 best options with risk analysis, impact estimates, and detailed reasoning. "
                "Use this after diagnosing an incident to understand remediation options."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "root_cause": {
                        "type": "string",
                        "description": "Identified root cause from diagnosis (e.g., 'congestion', 'hardware_failure')"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Diagnosis confidence (0.0-1.0)"
                    },
                    "hot_path": {
                        "type": "string",
                        "description": "Affected network path"
                    },
                    "latency_current": {
                        "type": "number",
                        "description": "Current latency in milliseconds"
                    },
                    "loss_current": {
                        "type": "number",
                        "description": "Current packet loss percentage"
                    },
                    "utilization": {
                        "type": "object",
                        "description": "Utilization by segment",
                        "additionalProperties": {"type": "number"}
                    }
                },
                "required": ["root_cause", "hot_path"]
            }
        ),
        Tool(
            name="show_commands",
            description=(
                "Generate exact CLI commands for a specific remediation playbook. "
                "Returns personalized commands with verification steps, rollback procedure, and safety warnings. "
                "Use this when an engineer wants to see the specific commands to execute."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "playbook_id": {
                        "type": "string",
                        "description": "Playbook ID (e.g., 'qos_traffic_shaping', 'partial_traffic_offload', 'config_rollback')"
                    },
                    "hot_path": {
                        "type": "string",
                        "description": "Affected network path"
                    },
                    "latency_current": {
                        "type": "number",
                        "description": "Current latency"
                    },
                    "loss_current": {
                        "type": "number",
                        "description": "Current packet loss"
                    },
                    "include_verification": {
                        "type": "boolean",
                        "description": "Include verification steps (default: true)"
                    },
                    "include_rollback": {
                        "type": "boolean",
                        "description": "Include rollback procedure (default: true)"
                    }
                },
                "required": ["playbook_id", "hot_path"]
            }
        ),
        Tool(
            name="generate_rca",
            description=(
                "Generate a comprehensive Root Cause Analysis (RCA) report in markdown format. "
                "Creates a professional post-incident report with timeline, analysis, and recommendations. "
                "Use this after an incident is resolved to document what happened."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "string",
                        "description": "Unique incident identifier"
                    },
                    "timestamp_start": {
                        "type": "string",
                        "description": "Incident start time (ISO format)"
                    },
                    "timestamp_end": {
                        "type": "string",
                        "description": "Incident end time (ISO format)"
                    },
                    "hot_path": {
                        "type": "string",
                        "description": "Affected network path"
                    },
                    "metrics": {
                        "type": "object",
                        "description": "Incident metrics (latency_ms, loss_pct, util_pct arrays)",
                        "properties": {
                            "latency_ms": {"type": "array", "items": {"type": "number"}},
                            "loss_pct": {"type": "array", "items": {"type": "number"}},
                            "util_pct": {"type": "object"}
                        }
                    },
                    "actions_taken": {
                        "type": "array",
                        "description": "Actions taken during incident resolution",
                        "items": {"type": "string"}
                    },
                    "resolution_summary": {
                        "type": "string",
                        "description": "Summary of how incident was resolved"
                    },
                    "engineer_notes": {
                        "type": "string",
                        "description": "Additional engineer notes (optional)"
                    }
                },
                "required": ["incident_id", "timestamp_start", "hot_path", "actions_taken", "resolution_summary"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls from MCP clients"""
    try:
        logger.info(f"Tool called: {name}")
        logger.debug(f"Arguments: {arguments}")
        
        if name == "diagnose_incident":
            return await handle_diagnose_incident(arguments)
        
        elif name == "recommend_actions":
            return await handle_recommend_actions(arguments)
        
        elif name == "show_commands":
            return await handle_show_commands(arguments)
        
        elif name == "generate_rca":
            return await handle_generate_rca(arguments)
        
        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
    
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]


async def handle_diagnose_incident(args: dict) -> list[TextContent]:
    """Handle diagnose_incident tool call"""
    # Build incident data
    incident_data = {
        "hot_path": args.get("hot_path", "Unknown"),
        "metrics": {
            "latency_ms": [args.get("latency_baseline", 45), args.get("latency_current", 45)],
            "loss_pct": [args.get("loss_baseline", 0.05), args.get("loss_current", 0.05)],
            "util_pct": args.get("utilization", {}),
        },
        "actions_taken": args.get("recent_changes", []),
        "timestamp_start": "",
        "latency_current": args.get("latency_current"),
        "latency_baseline": args.get("latency_baseline", 45),
        "loss_current": args.get("loss_current"),
        "loss_baseline": args.get("loss_baseline", 0.05),
        "utilization": args.get("utilization", {}),
    }
    
    # Run diagnosis
    result = copilot.diagnose(incident_data)
    
    # Format response
    response = f"""## Incident Diagnosis

**Root Cause:** {result['root_cause']}
**Confidence:** {int(result['confidence'] * 100)}%
**Severity:** {result['severity']}

### Evidence
"""
    
    if result.get('evidence'):
        for evidence in result['evidence']:
            response += f"- {evidence}\n"
    else:
        response += "- High latency detected\n"
        response += f"- Current: {args.get('latency_current')}ms vs Baseline: {args.get('latency_baseline', 45)}ms\n"
    
    response += "\n### Next Steps\n"
    response += "1. Use `recommend_actions` to see remediation options\n"
    response += "2. Review recommendations and choose appropriate action\n"
    response += "3. Use `show_commands` to get execution details\n"
    
    return [TextContent(type="text", text=response)]


async def handle_recommend_actions(args: dict) -> list[TextContent]:
    """Handle recommend_actions tool call"""
    # Build diagnosis
    diagnosis = {
        "root_cause": args.get("root_cause", "unknown"),
        "confidence": args.get("confidence", 0.5),
    }
    
    # Build context
    context = {
        "hot_path": args.get("hot_path"),
        "latency_current": args.get("latency_current"),
        "loss_current": args.get("loss_current"),
        "utilization": args.get("utilization", {}),
    }
    
    # Get recommendations
    result = copilot.recommend(diagnosis, context, top_n=3)
    
    # Format response
    response = f"""## Remediation Recommendations

**Root Cause:** {result['root_cause']}
**Confidence:** {int(result['confidence'] * 100)}%
**Recommended:** {result['recommended']}

---

"""
    
    for option in result['options']:
        response += f"""### Option {option['rank']}: {option['name']}

**ID:** `{option['id']}`
**Risk:** {option['risk_level']} | **Impact:** {option['estimated_impact']}
**Time to Effect:** {option['time_to_effect']} | **Success Rate:** {option['success_rate']}

**Description:** {option['description']}

**Reasoning:** {option['reasoning']}

**When to Use:** {option['when_to_use']}

---

"""
    
    response += "\n### Next Steps\n"
    response += f"To see commands for recommended option:\n"
    response += f"`show_commands` with playbook_id: `{result['recommended']}`\n"
    
    return [TextContent(type="text", text=response)]


async def handle_show_commands(args: dict) -> list[TextContent]:
    """Handle show_commands tool call"""
    # Build context
    context = {
        "hot_path": args.get("hot_path"),
        "latency_current": args.get("latency_current", 125),
        "loss_current": args.get("loss_current", 2.0),
        "latency_baseline": 45,
        "loss_baseline": 0.05,
    }
    
    # Generate commands
    result = copilot.generate_commands(
        playbook_id=args.get("playbook_id"),
        incident_context=context,
        include_verification=args.get("include_verification", True),
        include_rollback=args.get("include_rollback", True)
    )
    
    if "error" in result:
        return [TextContent(type="text", text=f"Error: {result['error']}")]
    
    # Format response
    response = f"""## CLI Commands: {result['playbook_name']}

**Risk Level:** {result['risk_level']}
**Time to Effect:** {result['time_to_effect']}
**Expected Impact:** {result['estimated_impact']}
**Execution Time:** {result['estimated_execution_time']}

### Prerequisites
"""
    
    for prereq in result['prerequisites']:
        response += f"- {prereq}\n"
    
    response += "\n### Safety Warnings\n"
    for warning in result['safety_warnings']:
        response += f"{warning}\n"
    
    response += "\n### Commands to Execute\n\n```bash\n"
    response += result['commands']
    response += "\n```\n"
    
    if result.get('verification'):
        response += "\n### Verification Steps\n"
        response += f"{result['verification']['what_to_check']}\n\n"
        for step in result['verification']['steps']:
            response += f"- {step}\n"
        
        response += "\n**Success Indicators:**\n"
        for indicator in result['verification']['success_indicators']:
            response += f"- {indicator}\n"
    
    if result.get('rollback'):
        response += "\n### Rollback Procedure (if needed)\n\n```bash\n"
        response += result['rollback']
        response += "\n```\n"
    
    response += "\n---\n\n"
    response += "⚠️ **IMPORTANT:** Review all commands carefully before executing.\n"
    response += "Always ensure you have proper backups and change approvals.\n"
    
    return [TextContent(type="text", text=response)]


async def handle_generate_rca(args: dict) -> list[TextContent]:
    """Handle generate_rca tool call"""
    # Build IncidentData
    try:
        incident = IncidentData(
            incident_id=args.get("incident_id"),
            timestamp_start=args.get("timestamp_start"),
            timestamp_end=args.get("timestamp_end", args.get("timestamp_start")),
            hot_path=args.get("hot_path"),
            metrics=args.get("metrics", {
                "latency_ms": [45, 125],
                "loss_pct": [0.05, 2.1],
                "util_pct": {}
            }),
            actions_taken=args.get("actions_taken", []),
            resolution_summary=args.get("resolution_summary"),
            engineer_notes=args.get("engineer_notes"),
        )
        
        # Generate RCA
        rca = copilot.generate_rca(incident)
        
        return [TextContent(type="text", text=rca)]
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error generating RCA: {str(e)}\n\nPlease ensure all required fields are provided."
        )]


async def main():
    """Run the MCP server"""
    logger.info("Starting Network Incident Copilot MCP Server...")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

