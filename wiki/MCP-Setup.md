# MCP Setup (Claude Desktop)

Derived from `CLAUDE_DESKTOP_SETUP.md`, `CONFIGURATION_SUMMARY.md`.

## Options
- Direct MCP (`mcp_server/server.py`): stateless tools (diagnose, recommend, commands, rca)
- LangGraph MCP (`mcp_server/langgraph_server.py`): workflow tools (start/approve/status/history/select)

## Configure (macOS)
```bash
# Direct MCP
cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# OR LangGraph MCP
cp claude_desktop_config_langgraph.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```
Update absolute paths inside the file(s), restart Claude Desktop.

## Verify
Ask: "What MCP tools do you have?"
- Direct: diagnose_incident, recommend_actions, show_commands, generate_rca
- LangGraph: start_incident_workflow, get_workflow_status, approve_diagnosis, approve_commands, get_workflow_history, select_playbook

See also: [MCP Tools](MCP-Tools.md).

