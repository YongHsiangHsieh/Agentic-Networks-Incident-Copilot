"""
RCA Generator - AI-powered Root Cause Analysis report generation.

This agent takes post-incident data and generates a comprehensive,
professional RCA document that engineers can review and submit.

Focus: Simple, clean, effective.
"""

from langchain_aws.chat_models.bedrock_converse import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Dict, Any
from datetime import datetime

from app.ai_config import AIConfig
from app.agents.root_cause_agent import get_agent as get_root_cause_agent
from app.models import IncidentData


class RCAGenerator:
    """Generates professional RCA reports from incident data."""
    
    def __init__(self):
        """Initialize with Claude on AWS Bedrock."""
        if AIConfig.DEBUG_AI:
            print(f"Initializing RCAGenerator with {AIConfig.BEDROCK_MODEL}")
        
        self.llm = ChatBedrockConverse(
            model=AIConfig.BEDROCK_MODEL,
            region_name=AIConfig.BEDROCK_REGION,
            temperature=0.3,  # Slightly higher for better narrative
            max_tokens=4000   # Longer for full RCA
        )
        
        # Reuse our root cause diagnosis agent
        self.root_cause_agent = get_root_cause_agent()
    
    def generate(self, incident: IncidentData) -> Dict[str, Any]:
        """
        Generate RCA report from incident data.
        
        Args:
            incident: Post-incident data including metrics, actions, resolution
        
        Returns:
            {
                'markdown': Full RCA in markdown format,
                'root_cause': Diagnosed root cause,
                'confidence': Confidence in diagnosis (0-1)
            }
        """
        print(f"\n📝 Generating RCA for {incident.incident_id}...")
        
        # Step 1: Run root cause analysis
        print("   1. Analyzing root cause...")
        root_cause_analysis = self._diagnose_root_cause(incident)
        
        # Step 2: Build incident context
        print("   2. Building incident context...")
        incident_context = self._format_incident_context(incident, root_cause_analysis)
        
        # Step 3: Generate RCA narrative
        print("   3. Generating RCA narrative...")
        rca_markdown = self._generate_rca_narrative(
            incident, 
            incident_context,
            root_cause_analysis
        )
        
        print("   ✓ RCA generation complete!")
        
        return {
            'markdown': rca_markdown,
            'root_cause': root_cause_analysis['cause'],
            'confidence': root_cause_analysis['confidence']
        }
    
    def _diagnose_root_cause(self, incident: IncidentData) -> Dict[str, Any]:
        """Run AI root cause diagnosis (reuse existing agent)."""
        
        # Build state for root cause agent
        # Calculate baseline/current metrics
        metrics = incident.metrics
        
        baseline_latency = sum(metrics.latency_ms[:3]) / 3
        current_latency = metrics.latency_ms[-1]
        baseline_loss = sum(metrics.loss_pct[:3]) / 3
        current_loss = metrics.loss_pct[-1]
        
        # Calculate utilization
        all_utils = []
        for segment, util_series in metrics.util_pct.items():
            if util_series:
                all_utils.extend(util_series)
        util_peak = max(all_utils) if all_utils else 0
        
        state = {
            'signals': {
                'baseline_latency_ms': baseline_latency,
                'current_latency_ms': current_latency,
                'delta_latency_ms': current_latency - baseline_latency,
                'baseline_loss_pct': baseline_loss,
                'current_loss_pct': current_loss,
                'delta_loss_pct': current_loss - baseline_loss,
                'util_peak': util_peak
            },
            'change_context': {
                'recent_changes': incident.recent_changes or False,
                'change_details': incident.change_details or ''
            },
            'bundle': {
                'hot_path': incident.hot_path,
                'metrics': {
                    'latency_ms': metrics.latency_ms,
                    'loss_pct': metrics.loss_pct,
                    'util_pct': metrics.util_pct
                },
                'window': {
                    'start_ts': incident.timestamp_start,
                    'end_ts': incident.timestamp_end
                },
                'incident_id': incident.incident_id,
                'policy': {
                    'latency_target_ms': 50  # Default SLA
                }
            }
        }
        
        # Run diagnosis
        return self.root_cause_agent.analyze(state)
    
    def _format_incident_context(
        self, 
        incident: IncidentData,
        root_cause: Dict[str, Any]
    ) -> str:
        """Build rich context for RCA generation."""
        
        # Calculate duration
        try:
            start = datetime.fromisoformat(incident.timestamp_start.replace('Z', '+00:00'))
            end = datetime.fromisoformat(incident.timestamp_end.replace('Z', '+00:00'))
            duration_minutes = int((end - start).total_seconds() / 60)
        except:
            duration_minutes = 0
        
        # Calculate impact metrics
        metrics = incident.metrics
        baseline_latency = sum(metrics.latency_ms[:3]) / 3
        peak_latency = max(metrics.latency_ms)
        latency_increase_pct = ((peak_latency - baseline_latency) / baseline_latency * 100) if baseline_latency > 0 else 0
        
        baseline_loss = sum(metrics.loss_pct[:3]) / 3
        peak_loss = max(metrics.loss_pct)
        
        context = f"""## INCIDENT OVERVIEW

**Incident ID**: {incident.incident_id}
**Start Time**: {incident.timestamp_start}
**End Time**: {incident.timestamp_end}
**Duration**: {duration_minutes} minutes
**Affected Path**: {incident.hot_path}

## IMPACT METRICS

**Latency Impact**:
- Baseline: {baseline_latency:.1f}ms
- Peak: {peak_latency:.1f}ms
- Increase: {latency_increase_pct:.0f}%

**Packet Loss Impact**:
- Baseline: {baseline_loss:.2f}%
- Peak: {peak_loss:.2f}%

**Metric Timeline**:
- Latency (ms): {metrics.latency_ms}
- Loss (%): {metrics.loss_pct}

## ROOT CAUSE DIAGNOSIS

**Identified Cause**: {root_cause['cause']}
**Confidence**: {root_cause['confidence']}

**Analysis**:
{root_cause['reasoning']}

**Contributing Factors**:
{self._format_list(root_cause.get('contributing_factors', []))}

## ACTIONS TAKEN

{self._format_actions(incident.actions_taken)}

## RESOLUTION

{incident.resolution_summary}

"""
        
        if incident.engineer_notes:
            context += f"""
## ENGINEER NOTES

{incident.engineer_notes}
"""
        
        return context
    
    def _format_list(self, items: list) -> str:
        """Format list items as markdown bullets."""
        if not items:
            return "- None identified"
        return "\n".join([f"- {item}" for item in items])
    
    def _format_actions(self, actions: list) -> str:
        """Format actions chronologically."""
        if not actions:
            return "- No specific actions logged"
        
        formatted = []
        for i, action in enumerate(actions, 1):
            formatted.append(f"{i}. {action}")
        return "\n".join(formatted)
    
    def _generate_rca_narrative(
        self,
        incident: IncidentData,
        context: str,
        root_cause: Dict[str, Any]
    ) -> str:
        """Use AI to generate professional RCA narrative."""
        
        prompt = self._get_rca_prompt(context, root_cause)
        
        try:
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            return response.content
            
        except Exception as e:
            print(f"   ⚠️ AI generation failed, using template: {e}")
            return self._fallback_template(incident, context, root_cause)
    
    def _get_system_prompt(self) -> str:
        """Define RCA writer expertise."""
        return """You are an experienced Site Reliability Engineer writing post-incident Root Cause Analysis (RCA) reports.

Your reports are:
- **Professional**: Clear, structured, well-formatted
- **Factual**: Based on data, not speculation
- **Actionable**: Include specific prevention steps
- **Blameless**: Focus on systems, not people
- **Readable**: For both technical engineers and managers

You write in past tense (incident already happened) and focus on learning, not blaming."""
    
    def _get_rca_prompt(self, context: str, root_cause: Dict[str, Any]) -> str:
        """Build prompt for RCA generation."""
        return f"""Write a comprehensive Root Cause Analysis report for this incident.

{context}

Generate a professional RCA report with the following sections:

## 1. Executive Summary
Write 2-3 sentences summarizing:
- What happened (the symptom)
- What caused it (root cause)
- How it was resolved
Keep it clear for non-technical managers.

## 2. Incident Timeline
Create a chronological timeline with timestamps showing:
- When the incident started
- Key investigation milestones
- When root cause was identified
- When remediation was applied
- When incident was resolved
Use the metric timeline data to be specific.

## 3. Impact Assessment

**Severity**: [Critical/High/Medium/Low - based on the metrics]

**Duration**: [Calculate from timestamps]

**User Impact**: [Describe the actual user experience based on latency/loss]

**Business Impact**: [Estimate based on severity and duration]

## 4. Root Cause Analysis

Explain the root cause in detail:
- What was the underlying problem?
- Why did it happen?
- What evidence supports this diagnosis?
- Include specific metric values as evidence

Use the diagnosis provided but expand with technical details.
Be specific and technical but still clear.

## 5. Resolution Steps

List the actions taken chronologically:
- What was done
- When it was done  
- Why that action was chosen
- How it helped resolve the issue

## 6. Lessons Learned

**What Went Well**:
- What helped us detect the issue quickly?
- What tools/processes worked well?

**What Could Be Improved**:
- What slowed down detection or resolution?
- What information was missing?
- What tools/processes need improvement?

## 7. Action Items & Prevention

List specific, actionable items to prevent recurrence:
- [ ] Monitoring improvements (be specific)
- [ ] Alerting improvements (be specific)
- [ ] Architecture/code changes (be specific)
- [ ] Documentation updates (be specific)
- [ ] Process improvements (be specific)

Each action item should be:
- Specific (not vague)
- Actionable (someone can do it)
- Preventive (addresses root cause)

---

**IMPORTANT GUIDELINES**:
- Use past tense (incident already happened)
- Be specific with numbers and timestamps
- Focus on facts, not opinions
- Be blameless (system issues, not people)
- Make it readable (use formatting, bullets, clear headers)
- Include code/command examples where relevant
- Use the actual data provided, don't make up numbers

Generate the complete RCA report now:"""
    
    def _fallback_template(
        self,
        incident: IncidentData,
        context: str,
        root_cause: Dict[str, Any]
    ) -> str:
        """Fallback template if AI fails."""
        
        return f"""# Incident Report: {incident.incident_id}

## Executive Summary

On {incident.timestamp_start}, an incident occurred affecting {incident.hot_path}. 
The root cause was identified as {root_cause['cause']}. 
The incident was resolved by {incident.resolution_summary}.

## Incident Timeline

- **Start**: {incident.timestamp_start}
- **End**: {incident.timestamp_end}

## Impact Assessment

**Severity**: High

**Affected Services**: {incident.hot_path}

## Root Cause Analysis

**Identified Cause**: {root_cause['cause']}

**Analysis**:
{root_cause['reasoning']}

## Resolution Steps

{self._format_actions(incident.actions_taken)}

**Resolution**: {incident.resolution_summary}

## Action Items

- [ ] Review monitoring for similar incidents
- [ ] Update runbooks based on this incident
- [ ] Implement preventive measures

---

*Note: This RCA was generated using a fallback template. Please review and expand with additional details.*
"""


# Singleton instance
_generator_instance = None


def get_generator() -> RCAGenerator:
    """Get or create the singleton RCA generator instance."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = RCAGenerator()
    return _generator_instance

