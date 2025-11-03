"""
AI-powered root cause analysis agent using AWS Bedrock.
"""

from langchain_aws.chat_models.bedrock_converse import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.ai_config import AIConfig


class RootCauseHypothesis(BaseModel):
    """Structured root cause analysis output from AI."""
    cause: str = Field(
        description="Primary root cause: 'congestion', 'config_regression', 'hardware_failure', etc."
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0",
        ge=0.0,
        le=1.0
    )
    reasoning: str = Field(
        description="Detailed step-by-step analysis explaining the diagnosis"
    )
    contributing_factors: List[str] = Field(
        description="Additional factors contributing to the issue",
        default_factory=list
    )
    next_steps: List[str] = Field(
        description="Recommended investigation steps",
        default_factory=list
    )


class RootCauseAgent:
    """AWS Bedrock-powered root cause analysis agent."""
    
    def __init__(self):
        """Initialize with Claude on AWS Bedrock."""
        if AIConfig.DEBUG_AI:
            print(f"Initializing RootCauseAgent with {AIConfig.BEDROCK_MODEL}")
        
        self.llm = ChatBedrockConverse(
            model=AIConfig.BEDROCK_MODEL,
            region_name=AIConfig.BEDROCK_REGION,
            temperature=AIConfig.LLM_TEMPERATURE,
            max_tokens=AIConfig.LLM_MAX_TOKENS,
        )
        
        # Use structured output for type-safe responses
        self.structured_llm = self.llm.with_structured_output(RootCauseHypothesis)
    
    def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze incident and generate root cause hypothesis using AI.
        
        Args:
            state: IncidentState dict with signals, change_context, bundle
            
        Returns:
            Hypothesis dict with cause, confidence, reasoning, etc.
        """
        try:
            if AIConfig.DEBUG_AI:
                print("Starting AI root cause analysis...")
            
            # Build context for analysis
            context = self._build_context(state)
            
            # Create messages
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=self._get_analysis_prompt(context))
            ]
            
            # Invoke LLM with structured output
            result: RootCauseHypothesis = self.structured_llm.invoke(messages)
            
            if AIConfig.DEBUG_AI:
                print(f"AI Analysis Result: {result.cause} (confidence: {result.confidence})")
            
            # Convert Pydantic model to dict
            return {
                "cause": result.cause,
                "confidence": result.confidence,
                "reasoning": result.reasoning,
                "details": result.reasoning,  # Backward compatibility
                "contributing_factors": result.contributing_factors,
                "next_steps": result.next_steps
            }
            
        except Exception as e:
            print(f"ERROR in AI analysis: {str(e)}")
            if AIConfig.FALLBACK_ON_ERROR:
                print("Falling back to rule-based analysis...")
                return self._fallback_analysis(state)
            else:
                raise
    
    def _get_system_prompt(self) -> str:
        """Define the AI agent's expertise and role."""
        return """You are an expert network incident analyst with 15+ years of experience in:
- Root cause diagnosis using evidence-based analysis
- Configuration change impact assessment and rollback analysis
- Network performance degradation troubleshooting
- Validation of hypotheses against contradicting signals

Your mission: Analyze network incidents and provide accurate, validated root cause diagnoses.

**DIAGNOSTIC CRITERIA TABLE** (Use this to validate your diagnosis):

| Root Cause | Utilization | Latency | Loss | Recent Changes | Typical Confidence |
|------------|-------------|---------|------|----------------|-------------------|
| **Congestion** | >85% 🔴 | High ↑ | High ↑ | Any | 0.8-0.9 |
| **Config Regression** | Any | Any | Any | YES + Correlated | 0.7-0.8 |
| **Hardware Failure** | <70% | Any | Very High (>10%) | None | 0.7-0.8 |
| **Routing Issue** | <70% | High ↑ | Low/Medium | Routing changes | 0.6-0.7 |
| **Quality Issue** | <70% | Moderate | Low | High jitter | 0.6-0.7 |
| **Unknown/Ambiguous** | Any | Any | Any | Contradictory signals | 0.3-0.5 |

**CRITICAL: If utilization is <70%, congestion is UNLIKELY. Consider routing, hardware, or quality issues instead.**

Analysis methodology:
1. Read ALL metrics before forming hypothesis (avoid anchoring bias)
2. Check utilization FIRST - it determines if congestion is possible
3. For each hypothesis, list evidence that SUPPORTS and CONTRADICTS it
4. Validate: Does your hypothesis match the diagnostic criteria?
5. If signals contradict your hypothesis, LOWER confidence significantly
6. Consider timing correlation with changes
7. State contradictions explicitly if they exist

Be thorough, evidence-based, and acknowledge contradictions."""
    
    def _get_analysis_prompt(self, context: str) -> str:
        """Create analysis prompt with incident context."""
        return f"""Analyze this network incident and determine the root cause.

{context}

**ANALYSIS WORKFLOW** (Follow this order):

1. **Read Utilization FIRST**: 
   - Is utilization >85%? If YES, congestion is likely. If NO (<70%), congestion is UNLIKELY.
   
2. **Pattern Analysis**: What do ALL metrics reveal?
   - Latency trends
   - Loss trends
   - Utilization trends
   
3. **Hypothesis Formation**: Based on metrics, what are the possible causes?

4. **CRITICAL VALIDATION STEP** (Do NOT skip this):
   
   **For EACH hypothesis you consider, answer:**
   
   a) If you suspect **CONGESTION**:
      - Is utilization >85%? ☐ YES ☐ NO
      - If NO, congestion is UNLIKELY. What else could cause high latency?
   
   b) If you suspect **CONFIG REGRESSION**:
      - Did changes occur BEFORE symptoms started? ☐ YES ☐ NO
      - Does timing strongly correlate? ☐ YES ☐ NO
   
   c) For ANY diagnosis:
      - **Supporting Evidence**: Which metrics SUPPORT this hypothesis?
      - **Contradicting Evidence**: Which metrics CONTRADICT this hypothesis?
      - **If contradictions exist**: State them explicitly and LOWER confidence to 0.3-0.5
   
5. **Change Correlation**: Do any changes correlate with symptom onset?

6. **Root Cause Conclusion**: 
   - What is the most likely root cause based on ALL evidence?
   - Explicitly state if your confidence is lowered due to contradictions
   
7. **Confidence Calibration**:
   - 0.9-1.0: Single clear cause, all signals align, no contradictions
   - 0.7-0.8: Likely cause, most signals support, minor ambiguity  
   - 0.5-0.6: Multiple plausible causes, some contradictions
   - 0.3-0.4: Significant contradictions, insufficient data
   
8. **Contributing Factors**: What else might be involved?

9. **Next Steps**: What should be investigated to confirm or rule out alternatives?

**IMPORTANT**: If you find contradicting signals (e.g., high latency but LOW utilization), you MUST:
- State the contradiction explicitly
- Lower your confidence
- Suggest alternative hypotheses

Think step-by-step, validate against ALL metrics, and provide evidence-based conclusions."""
    
    def _build_context(self, state: Dict[str, Any]) -> str:
        """Build rich context for AI analysis."""
        signals = state.get('signals', {})
        change_context = state.get('change_context', {})
        bundle = state.get('bundle', {})  # Bundle is a dict when state is dumped
        
        # Extract metrics
        delta_latency = signals.get('delta_latency_ms', 0)
        delta_loss = signals.get('delta_loss_pct', 0)
        util_peak = signals.get('util_peak', 0)
        baseline_latency = signals.get('baseline_latency_ms', 0)
        current_latency = signals.get('current_latency_ms', 0)
        baseline_loss = signals.get('baseline_loss_pct', 0)
        current_loss = signals.get('current_loss_pct', 0)
        
        # Calculate degradation percentages
        latency_pct = (delta_latency / baseline_latency * 100) if baseline_latency > 0 else 0
        loss_multiplier = (current_loss / baseline_loss) if baseline_loss > 0 else 0
        
        # FIX #1: Calculate utilization degradation metrics (symmetric with latency/loss)
        metrics = bundle.get('metrics', {})
        util_pct_dict = metrics.get('util_pct', {})
        
        # Calculate baseline utilization (average of first 3 values across all segments)
        baseline_utils = []
        current_utils = []
        for segment, util_series in util_pct_dict.items():
            if util_series and len(util_series) > 0:
                baseline_utils.append(sum(util_series[:3]) / min(3, len(util_series)))
                current_utils.append(util_series[-1])
        
        baseline_util = sum(baseline_utils) / len(baseline_utils) if baseline_utils else 0
        current_util_avg = sum(current_utils) / len(current_utils) if current_utils else util_peak
        delta_util = current_util_avg - baseline_util
        util_pct_change = (delta_util / baseline_util * 100) if baseline_util > 0 else 0
        
        # Determine congestion indicator based on utilization
        if util_peak > 85:
            congestion_indicator = "🔴 HIGH (>85%) - Strong congestion indicator"
        elif util_peak > 70:
            congestion_indicator = "🟡 MEDIUM (70-85%) - Possible congestion"
        elif util_peak > 50:
            congestion_indicator = "🟢 MODERATE (50-70%) - Unlikely to be pure congestion"
        else:
            congestion_indicator = "🟢 LOW (<50%) - Congestion UNLIKELY - Consider routing/hardware/quality issues"
        
        # Extract bundle fields (dict access)
        hot_path = bundle.get('hot_path', 'N/A')
        policy = bundle.get('policy', {})
        latency_target = policy.get('latency_target_ms', 0)
        metrics = bundle.get('metrics', {})
        window = bundle.get('window', {})
        incident_id = bundle.get('incident_id', 'N/A')
        
        # FIX #2: Reorder metrics - Put utilization FIRST to prevent anchoring bias
        # Build structured context
        context = f"""## INCIDENT ANALYSIS DATA

### Metrics Summary (Ordered by Diagnostic Priority)

**🚦 UTILIZATION** (Primary Congestion Indicator):
- Baseline: {baseline_util:.1f}%
- Current (peak): {util_peak:.1f}%
- Average Current: {current_util_avg:.1f}%
- Delta: {delta_util:+.1f}%
- Change: {util_pct_change:+.0f}% increase
- **Congestion Indicator**: {congestion_indicator}

**Latency:**
- Baseline: {baseline_latency:.1f} ms
- Current: {current_latency:.1f} ms
- Delta: {delta_latency:+.1f} ms ({latency_pct:+.0f}% change)

**Packet Loss:**
- Baseline: {baseline_loss:.2f}%
- Current: {current_loss:.2f}%
- Delta: {delta_loss:+.2f}%
- Multiplier: {loss_multiplier:.1f}x

### Network Topology
- Hot path: {hot_path}
- Policy latency target: {latency_target} ms
- **SLA Status**: {'⚠️ VIOLATED - latency exceeds target' if current_latency > latency_target else '✓ Within target'}

### Time Series Trends
**Latency progression (ms):**
{self._format_series(metrics.get('latency_ms', [])[-10:])}

**Loss progression (%):**
{self._format_series(metrics.get('loss_pct', [])[-10:])}

### Per-Segment Utilization"""
        
        # Add utilization details
        util_pct = metrics.get('util_pct', {})
        for segment, util_series in util_pct.items():
            if util_series:
                current = util_series[-1]
                baseline_util = util_series[0] if util_series else 0
                delta_util = current - baseline_util
                trend = "↑ RISING" if delta_util > 5 else "→ STABLE" if abs(delta_util) <= 5 else "↓ FALLING"
                context += f"\n- {segment}: {current:.0f}% ({trend}, Δ{delta_util:+.0f}%)"
        
        # Add change information
        recent_change = change_context.get('recent_change', False)
        if recent_change:
            context += "\n\n### Recent Changes Detected: ⚠️ YES"
            context += "\n**Timeline correlation is CRITICAL:**"
            for event in change_context.get('events', []):
                context += f"\n- {event['ts']}: {event['type']} on {event['scope']}"
        else:
            context += "\n\n### Recent Changes Detected: ✓ NO"
            context += "\n(No configuration or deployment changes in incident window)"
        
        # Add incident window info
        context += f"\n\n### Incident Window"
        context += f"\n- Start: {window.get('start_ts', 'N/A')}"
        context += f"\n- End: {window.get('end_ts', 'N/A')}"
        context += f"\n- Incident ID: {incident_id}"
        
        return context
    
    def _format_series(self, series: list) -> str:
        """Format time series data for display."""
        if not series:
            return "No data"
        
        formatted = ", ".join([f"{v:.1f}" for v in series])
        return f"[{formatted}]"
    
    def _fallback_analysis(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Rule-based fallback if AI fails."""
        signals = state.get('signals', {})
        change_context = state.get('change_context', {})
        
        delta_latency = signals.get('delta_latency_ms', 0)
        delta_loss = signals.get('delta_loss_pct', 0)
        util_peak = signals.get('util_peak', 0)
        recent_change = change_context.get('recent_change', False)
        
        # Rule-based logic
        if delta_latency > 25 and delta_loss > 1.0 and util_peak >= 90:
            return {
                "cause": "congestion",
                "confidence": 0.8,
                "reasoning": "FALLBACK RULE: High latency increase (+{:.1f}ms), elevated packet loss (+{:.2f}%), and peak utilization ({:.0f}%) strongly indicate network congestion. The combination of these three factors is a classic congestion signature.".format(
                    delta_latency, delta_loss, util_peak
                ),
                "details": "High latency, packet loss, and utilization indicate network congestion",
                "contributing_factors": ["High utilization", "Capacity exhaustion", "Traffic spike"],
                "next_steps": [
                    "Verify traffic sources and destinations",
                    "Check for DDoS or unusual traffic patterns",
                    "Review capacity planning timeline"
                ]
            }
        elif recent_change:
            events = change_context.get('events', [])
            change_summary = ", ".join([f"{e['type']} on {e['scope']}" for e in events[:2]])
            return {
                "cause": "config_regression",
                "confidence": 0.6,
                "reasoning": f"FALLBACK RULE: Recent configuration changes detected ({change_summary}) shortly before incident onset. Timing correlation suggests change-induced issue.",
                "details": "Recent configuration change detected in hot path",
                "contributing_factors": ["Configuration change on hot path", "Timing correlation"],
                "next_steps": [
                    "Review change diff and validation",
                    "Compare before/after metrics",
                    "Consider rollback if appropriate"
                ]
            }
        else:
            return {
                "cause": "unknown_degradation",
                "confidence": 0.4,
                "reasoning": f"FALLBACK RULE: Service degradation detected (latency +{delta_latency:.1f}ms, loss +{delta_loss:.2f}%) but specific root cause unclear from available data. Metrics don't match common failure patterns.",
                "details": "Service degradation detected but cause unclear",
                "contributing_factors": [],
                "next_steps": [
                    "Gather additional telemetry data",
                    "Check application and system logs",
                    "Review historical trends for patterns"
                ]
            }


# Global agent instance (singleton pattern for efficiency)
_agent_instance = None


def get_agent() -> RootCauseAgent:
    """
    Get or create the singleton agent instance.
    Reusing the same instance across requests is more efficient.
    """
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = RootCauseAgent()
    return _agent_instance

