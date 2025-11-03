# Agents

Overview of the four specialized agents and their responsibilities.

## Root Cause Agent (`app/agents/root_cause_agent.py`)
- Purpose: Evidence-based diagnosis with structured output
- Inputs: signals (utilization/latency/loss deltas), change context
- Method: Natural-language context → Claude (Bedrock) → Pydantic model
- Safeguards: Explicit contradiction checks; rule-based fallback

## Recommendation Engine
- Rule-based: `app/agents/recommendation_engine.py` (multi-factor scoring)
- Hybrid: `app/agents/hybrid_recommendation_engine.py` (AI re-rank top N via Bedrock)
- Metadata used: risk, time to effect, cost, success rate, applicability

## Command Generator (`app/agents/command_generator.py`)
- Template-based command rendering with parameter substitution
- Safety validations, verification steps, rollback
- Produces warnings and success indicators

## RCA Generator (`app/agents/rca_generator.py`)
- Post-incident markdown report with executive summary, timeline, actions, lessons
- Reuses root cause analysis; focuses on low-risk, high-value documentation

See also: [Playbooks](Playbooks.md).

