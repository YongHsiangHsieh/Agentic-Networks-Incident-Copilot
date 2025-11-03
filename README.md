# 🚀 Network Incident Copilot

**AI-Powered Copilot for Network Incident Response (Production-focused, Human-in-the-loop)**

Transform incident response from hours to minutes with AI-guided diagnosis, hybrid recommendations, safe command generation, and instant RCA docs — while engineers stay in control.

[![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-orange)](https://aws.amazon.com/bedrock/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0-blue)](https://langchain.com)
[![MCP](https://img.shields.io/badge/MCP-Server-green)](https://modelcontextprotocol.io/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)

---

## ❓ Why This Exists (Thesis)

Incidents aren’t just technical — they’re socio-technical. Most tools optimize for metrics collection or automation, but leave engineers doing time-consuming analysis, decision-making, and documentation under pressure. Full autonomy is risky in production networks: safety, change windows, compliance, and accountability demand human judgment.

This copilot embraces that reality. It accelerates the parts that are slow and error-prone (reasoning, option ranking, command preparation, RCA writing) while keeping humans decisively in the loop. The result: consistently safer, faster outcomes without ceding control.

Core beliefs:

- Humans own risk; AI accelerates work. Approvals are mandatory at critical gates.
- Explainability beats magic. Every recommendation comes with reasoning, risk, impact, and alternatives.
- Durable state > stateless chat. Incidents are workflows with memory, not one-off prompts.
- Production first. Failure modes, fallbacks, and audit trails are design requirements, not afterthoughts.

---

## 📖 Read the Full Wiki

This README is a high-signal overview. The complete, extended documentation lives in the project Wiki and is the ultimate entry point for learning, architecture, setup, and deep dives:

- Start here: `wiki/Home.md` (locally) or the GitHub Wiki tab on the repository
- Highlights: Architecture, LangGraph workflow, Agents, Playbooks, API, MCP setup, Data integration, Testing, Production guidance

---

## 🧩 Problem We’re Solving

- Fragmented telemetry: metrics, logs, topology and change data live in different systems.
- Tribal knowledge: runbooks exist but are inconsistently applied; junior engineers struggle under pressure.
- High variance: human decisions vary incident to incident, causing uneven outcomes.
- Documentation burden: RCA writing is slow and often neglected.
- Automation risk: pushing changes without guardrails can make outages worse.

Success looks like: faster mean time to restore, safer actions with explicit approvals, consistent recommendations, and instant RCAs — all traceable in an audit trail.

---

## 🧭 Philosophy: Copilot, Not Autonomy

This system is an "agentifiable copilot" — not a fully autonomous agent. Engineers remain the pilot. The copilot accelerates analysis, suggests safe actions, and produces documentation, but key decisions (diagnosis acceptance, command approval) require human approval.

Non-goals:

- Replacing human judgment in risky changes
- Blind auto-remediation without approvals
- Becoming your monitoring stack (it complements, not replaces)

---

## 🏗️ Design Principles & Trade-offs

- Safety over speed: Human approvals are built-in; commands include verification and rollback.
- Hybrid recommendations: Rule-based scoring for speed and predictability; AI re-ranking for context sensitivity. Falls back cleanly to rule-based if AI is unavailable.
- Orchestrated, stateful workflows: LangGraph provides durable state and resumability across steps and approvals.
- Open interfaces: REST for systems integration; MCP for natural-language control via Claude Desktop.
- Single source of action truth: A structured playbook library encodes remediation steps, risks, and prerequisites.
- Auditability: Every decision and approval is written to history.

Trade-offs chosen now for production readiness:

- Push-only data ingestion (simple, reliable) over auto-pull (complex, vendor-specific)
- Simulated execution (safe) over device pushes (powerful but higher blast radius)
- In-memory state (fast) over persistent DB (to be added as adoption grows)

---

## 🧠 Tech Stack (What we use and why)

- LangGraph (stateful orchestration): Incidents are workflows, not chats. LangGraph gives durable state, checkpoints, human-in-the-loop interrupts, and conditional routing. That enables approvals, retries, branching, and audit trail by design.
- LangChain AWS (Bedrock integration): We use LangChain’s AWS integration to access Claude on Bedrock with IAM—no API keys. This provides reliable, enterprise-grade LLM access with structured outputs (Pydantic) and easy model swaps (Haiku → Sonnet).
- AWS Bedrock (Claude models): Claude is strong at analytical reasoning. We default to Haiku for speed/cost and can upgrade to Sonnet for harder tasks. Bedrock also aligns with enterprise security and deployment.
- MCP Server (Model Context Protocol): Exposes our capabilities as tools to Claude Desktop, enabling natural-language control of the entire workflow (start, approve, status, history, select playbooks). This reduces friction for engineers during incidents.
- FastAPI + Uvicorn: Solid, modern REST surface for systems integration, dashboards, and automation. Mirrors the MCP toolset for maximum flexibility.
- Pydantic v2: Typed, structured inputs/outputs everywhere for reliability, validation, and clear interfaces between components.

How they fit together:
- Interfaces (REST + MCP) call into a single Orchestrator facade.
- Orchestrator coordinates agents (Diagnosis → Recommendations → Commands → RCA) through LangGraph nodes with approval gates.
- Bedrock via LangChain AWS powers reasoning; rules provide graceful fallbacks.

### Tech decisions at a glance
- LangGraph over ad‑hoc orchestration: approval gates, resumability, conditional routing, and an audit trail are first‑class needs in incident workflows.
- Bedrock (Claude) via LangChain AWS: IAM‑secured access, easy model choice (Haiku/Sonnet), strong reasoning; fallbacks ensure reliability when AI is unavailable.
- MCP alongside REST: natural‑language control in Claude Desktop during an incident, plus programmable APIs for automation and UIs.

See the Wiki for deeper dives and examples: Architecture, LangGraph Workflow, MCP Tools, and Tech Stack pages.

---

## 🎯 What It Does

1. **Diagnoses** likely root causes from incident context
2. **Recommends** remediation playbooks (rule-based + AI re-ranked)
3. **Generates** safe, personalized CLI commands (with verification + rollback)
4. **Documents** professional RCA reports

---

## 🌟 Key Features

- **Hybrid AI Recommendations**: Rule-based scoring + AI re-ranking (Bedrock Claude)
- **LangGraph Orchestrator**: Durable, stateful workflow with human approval gates
- **MCP Server**: Natural language control via Claude Desktop
- **REST API**: Start/approve/review workflows programmatically
- **Audit Trail**: Every step and decision is recorded

---

## 🧪 End-to-End Scenario (Real-World Walkthrough)

Context: Peak traffic. Alerts show latency spike and 2% loss on `RouterB-RouterC`.

1. Start workflow (push known context):

```bash
curl -X POST http://localhost:8000/api/workflows/start \
  -H "Content-Type: application/json" \
  -d '{
    "incident_id": "INC-2451",
    "hot_path": "RouterB-RouterC",
    "latency_current": 125.0,
    "loss_current": 2.1,
    "priority": "high"
  }'
```

The orchestrator stores this as `incident_data` and runs diagnosis.

2. Review and approve diagnosis:

```bash
curl -X GET http://localhost:8000/api/workflows/INC-2451/status
curl -X POST http://localhost:8000/api/workflows/INC-2451/approve-diagnosis \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "feedback": "Consistent with telemetry"}'
```

3. Get recommendations and generate commands:

- The system ranks playbooks (e.g., QoS traffic shaping, partial offload) with reasoning and risk.
- Commands are generated from playbook templates using `incident_data` (e.g., `hot_path`).

4. (Optional) choose a different playbook:

```bash
curl -X POST http://localhost:8000/api/workflows/INC-2451/select-playbook \
  -H "Content-Type: application/json" \
  -d '{"playbook_id": "qos_traffic_shaping"}'
```

5. Approve commands:

```bash
curl -X POST http://localhost:8000/api/workflows/INC-2451/approve-commands \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "feedback": "Proceed in maintenance window"}'
```

6. Generate RCA (automatic at the end of the workflow):

- The system compiles an RCA with timeline, decisions, commands, and outcomes for stakeholders.

At every step, approvals and outputs are appended to `history` for audit.

---

## 📡 Data Model (Current)

- Push-only: The workflow uses the data you provide at start (or via MCP tool args). There’s no automatic fetching from Prometheus/CloudWatch/log stores yet.
- Key fields consumed today: `hot_path`, `latency_current`, `loss_current`, priority, and any extra you choose to include in `incident_data`.
- Command generation depends on these keys to fill playbook templates. Missing keys can lead to empty command lists.

---

## ⚙️ Quick Start

### 1) Install

```bash
pip install -r requirements.txt
```

### 2) Configure AWS (for Bedrock, optional but recommended)

Create `.env` or export env vars:

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
BEDROCK_MODEL=us.anthropic.claude-3-5-sonnet-20241022-v2:0
```

### 3) Run API

```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Open http://localhost:8000/docs
```

### 4) Minimal Workflow

```bash
# Start
curl -X POST http://localhost:8000/api/workflows/start \
  -H "Content-Type: application/json" \
  -d '{
    "incident_id": "INC-001",
    "hot_path": "RouterB-RouterC",
    "latency_current": 125.0,
    "loss_current": 2.1,
    "priority": "high"
  }'

# Approve diagnosis
curl -X POST http://localhost:8000/api/workflows/INC-001/approve-diagnosis \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "feedback": "LGTM"}'

# (Optionally) select a playbook
curl -X POST http://localhost:8000/api/workflows/INC-001/select-playbook \
  -H "Content-Type: application/json" \
  -d '{"playbook_id": "qos_traffic_shaping"}'

# Approve commands
curl -X POST http://localhost:8000/api/workflows/INC-001/approve-commands \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "feedback": "Proceed"}'
```

---

## 💬 Using Claude Desktop (MCP)

We provide **two MCP servers** for different use cases:

1. **Direct MCP Server** (`mcp_server/server.py`)

   - Quick Q&A, stateless
   - Config: `claude_desktop_config.json`
   - Tools: diagnose, recommend, commands, rca

2. **LangGraph MCP Server** (`mcp_server/langgraph_server.py`)
   - Production workflows with approval gates
   - Config: `claude_desktop_config_langgraph.json`
   - Tools: start_workflow, approve_diagnosis, approve_commands, status, history

**Setup instructions:** See `private_docs/CLAUDE_DESKTOP_SETUP.md` for detailed configuration guide.

**Quick setup:**

```bash
# Copy the config you want to use
cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Or use the LangGraph version
cp claude_desktop_config_langgraph.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Update the paths in the config file to match your system
# Then restart Claude Desktop
```

- In a chat, run tools like:
  - `start_incident_workflow(incident_id, hot_path, latency_current, loss_current, priority)`
  - `approve_diagnosis(incident_id, approved, feedback)`
  - `select_playbook(incident_id, playbook_id)`
  - `approve_commands(incident_id, approved, feedback)`
  - `get_workflow_status(incident_id)` / `get_workflow_history(incident_id)`

The MCP server mirrors the REST endpoints for natural language control.

---

## 🏗️ Architecture (High-level)

```
Interfaces → MCP Server / REST API
                 │
                 ▼
          LangGraph Orchestrator
  diagnose → recommend → commands → execute → rca
                 ▲             │
           human approvals ────┘
```

- Agents: `root_cause_agent`, `hybrid_recommendation_engine`, `command_generator`, `rca_generator`
- State: `IncidentState` stores incident_data, decisions, commands, results, and audit history
- Playbooks: structured templates with safety, verification, and rollback

---

## 📦 Project Structure

```
.
├── app/
│   ├── agents/                # AI agents (diagnosis, hybrid recommend, commands, RCA)
│   ├── langgraph_orchestrator/ # State, nodes, routing, graph
│   ├── api/                   # REST endpoints
│   ├── playbooks/             # Playbook library
│   ├── main.py                # FastAPI app
│   └── models.py
├── mcp_server/                # MCP server exposing workflow tools
├── tests/                     # Scenario fixtures and tests
├── requirements.txt
└── README.md
```

---

## 🧪 Testing

```bash
python3 test_copilot.py
# or focused flows
python3 test_langgraph_orchestrator.py
python3 test_production_enhancements.py
```

---

## ❗ Current Limitations (Important)

- **Push-only data model**: The workflow only uses data you provide when starting (or via tool args). No automatic fetch from Prometheus/CloudWatch/log stores yet.
- **Mid-run enrichment**: There is no public endpoint to append telemetry/logs during a running workflow.
- **Execution**: Commands are generated with safety scaffolding, but device-side execution is simulated (no live push to network gear).
- **State persistence**: In-memory via LangGraph `MemorySaver`. State resets on API server restart.
- **Bedrock optional**: If Bedrock isn’t configured, hybrid re-ranking falls back gracefully to rule-based only.
- **MCP setup**: Claude Desktop integration requires local configuration by the user.

---

## 🔮 Roadmap (Short)

- Real-time telemetry ingestion (push endpoints, Prometheus/CloudWatch connectors)
- Append logs/metrics mid-workflow and auto-consume latest in nodes
- Pluggable persistent checkpointer (Redis/Postgres)
- Optional command execution adapters with stronger safety gates
- Slack bot and simple web UI

---

## 🔭 Future Improvements (Planned)

These are near-term evolutions beyond the current prototype to make the system even more production-ready and flexible:

- Deployment via AWS Bedrock Agents: Package and operate the copilot using AWS Bedrock Agents/Agent Core for managed, secure runtime in AWS environments.
- Richer LangGraph branching and retries: In addition to human-in-the-loop, allow developers/engineers to branch, retry, or stop at any approval or decision point; different paths for different scenarios.
- From push-only to assisted fetch: Today you push incident context at start. We’ll add human-permissioned data fetchers so the system can pull metrics/logs/topology on demand (with explicit approvals), reducing manual data wrangling.
- Real-time monitoring integration: Begin with AWS services (e.g., CloudWatch/Prometheus connectors). On incident, the copilot can fetch the latest telemetry automatically (with human approval), so engineers don’t have to assemble the data first.

See the Wiki for implementation notes and integration options.

---

## 💼 Value

- Reduce MTTR dramatically with consistent, safe guidance
- Keep humans in control at critical decision points
- Produce executive-ready RCAs automatically

---

## 📄 License

MIT License

---

Made for engineers. Built as a copilot — so you stay the pilot. ✈️
