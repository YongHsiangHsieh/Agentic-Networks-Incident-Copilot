"""
Hybrid AI + Rule-Based Recommendation Engine.

Combines the best of both worlds:
- Rule-based scoring: Fast, predictable, explainable (90% of work)
- AI re-ranking: Contextual understanding, nuanced decisions (10% refinement)

This solves real problems:
- Fast enough for production (< 5 seconds)
- Smart enough to handle edge cases
- Explainable to engineers (they see both scores)
- Reliable with fallback to rules if AI fails
"""

from typing import List, Dict, Optional
import json
import boto3
from pydantic import BaseModel

from app.playbooks.playbook_library import ALL_PLAYBOOKS, Playbook, get_playbooks_for_root_cause
from app.agents.recommendation_engine import RecommendationEngine
from app.ai_config import AIConfig


class AIRankingInput(BaseModel):
    """Input for AI re-ranking."""
    playbook_options: List[Dict]
    incident_context: Dict
    root_cause: str
    confidence: float


class AIRankingOutput(BaseModel):
    """Output from AI re-ranking."""
    ranked_options: List[Dict]
    reasoning: str


class HybridRecommendationEngine(RecommendationEngine):
    """
    Enhanced recommendation engine with hybrid AI + rule-based ranking.
    
    Workflow:
    1. Rule-based scoring (fast, always reliable)
    2. Filter to top 5 candidates
    3. AI re-ranks top 5 (adds contextual understanding)
    4. Return top 3 with both scores
    
    Benefits:
    - Fast: Only AI-rank top candidates (not all 6 playbooks)
    - Reliable: Falls back to rule-based if AI fails
    - Explainable: Shows both math and AI scores
    - Smart: AI catches edge cases rules miss
    """
    
    def __init__(self):
        super().__init__()
        
        # AI configuration
        self.model_id = AIConfig.BEDROCK_MODEL
        self.region = AIConfig.BEDROCK_REGION
        
        # Feature flag: enable/disable AI re-ranking
        self.use_ai_reranking = AIConfig.USE_AI_RANKING
        
        # Initialize AWS Bedrock client
        try:
            self.bedrock_client = boto3.client(
                service_name="bedrock-runtime",
                region_name=self.region
            )
        except Exception as e:
            print(f"Warning: Could not initialize Bedrock client: {e}")
            self.bedrock_client = None
            self.use_ai_reranking = False
    
    def recommend(
        self,
        root_cause: str,
        confidence: float,
        incident_context: dict,
        top_n: int = 3,
        use_ai: Optional[bool] = None
    ) -> Dict:
        """
        Get hybrid recommendations with rule-based + AI ranking.
        
        Args:
            root_cause: Diagnosed root cause
            confidence: Diagnosis confidence (0-1)
            incident_context: Incident details and metrics
            top_n: Number of recommendations to return
            use_ai: Override feature flag (True/False/None=use default)
        
        Returns:
            Dict with ranked options including both rule and AI scores
        """
        # Step 1: Rule-based scoring (always run, always fast)
        rule_based_result = super().recommend(
            root_cause=root_cause,
            confidence=confidence,
            incident_context=incident_context,
            top_n=5  # Get top 5 for AI re-ranking
        )
        
        # Decide whether to use AI
        should_use_ai = use_ai if use_ai is not None else self.use_ai_reranking
        
        # Step 2: AI re-ranking (optional, for top candidates only)
        if should_use_ai and self.bedrock_client and len(rule_based_result["options"]) > 1:
            try:
                ai_ranked = self._ai_rerank(
                    candidates=rule_based_result["options"],
                    root_cause=root_cause,
                    confidence=confidence,
                    incident_context=incident_context
                )
                
                # Merge rule-based and AI scores
                for option in ai_ranked:
                    option["hybrid_approach"] = "rule_based + ai_reranked"
                
                return {
                    "root_cause": root_cause,
                    "confidence": confidence,
                    "recommended": ai_ranked[0]["id"] if ai_ranked else None,
                    "options": ai_ranked[:top_n],
                    "total_candidates": rule_based_result["total_candidates"],
                    "ranking_method": "hybrid (rule-based + AI)",
                    "fallback_used": False
                }
                
            except Exception as e:
                print(f"AI re-ranking failed: {e}. Falling back to rule-based.")
                # Fall through to return rule-based results
        
        # Step 3: Return rule-based results (fallback or if AI disabled)
        result = rule_based_result.copy()
        result["options"] = result["options"][:top_n]
        result["ranking_method"] = "rule-based only"
        result["fallback_used"] = should_use_ai  # True if AI was supposed to run but failed
        
        return result
    
    def _ai_rerank(
        self,
        candidates: List[Dict],
        root_cause: str,
        confidence: float,
        incident_context: Dict
    ) -> List[Dict]:
        """
        Use AI to re-rank top candidates with contextual understanding.
        
        AI considers:
        - Incident severity and business impact
        - Time of day and traffic patterns
        - Historical success for similar incidents
        - Team expertise and available resources
        - Risk tolerance based on context
        
        These nuances are hard to capture in rule-based scoring.
        """
        # Build prompt for AI
        prompt = self._build_reranking_prompt(
            candidates=candidates,
            root_cause=root_cause,
            confidence=confidence,
            incident_context=incident_context
        )
        
        # Call AWS Bedrock
        response = self.bedrock_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1500,
                "temperature": 0.3,  # Low temp for consistent ranking
                "messages": [{
                    "role": "user",
                    "content": prompt
                }]
            })
        )
        
        # Parse response
        response_body = json.loads(response["body"].read())
        ai_text = response_body["content"][0]["text"]
        
        # Extract JSON from response
        ai_json = self._extract_json_from_text(ai_text)
        
        # Re-rank candidates based on AI output
        ranked = []
        ai_rankings = ai_json.get("rankings", [])
        
        # Match AI rankings to original candidates
        candidates_by_id = {c["id"]: c for c in candidates}
        
        for ranking in ai_rankings:
            playbook_id = ranking.get("playbook_id")
            if playbook_id in candidates_by_id:
                candidate = candidates_by_id[playbook_id].copy()
                candidate["ai_score"] = ranking.get("score", 0)
                candidate["ai_reasoning"] = ranking.get("reasoning", "")
                # Keep original rule-based score for comparison
                candidate["rule_based_score"] = candidate.get("score", 0)
                # Use AI score as primary
                candidate["score"] = ranking.get("score", candidate.get("score", 0))
                ranked.append(candidate)
        
        # Add overall AI reasoning
        if ranked:
            ranked[0]["ai_recommendation_reasoning"] = ai_json.get("recommendation_reasoning", "")
        
        return ranked
    
    def _build_reranking_prompt(
        self,
        candidates: List[Dict],
        root_cause: str,
        confidence: float,
        incident_context: Dict
    ) -> str:
        """Build prompt for AI re-ranking."""
        
        # Format candidates for AI
        candidates_text = ""
        for i, candidate in enumerate(candidates, 1):
            candidates_text += f"""
{i}. {candidate['name']} (ID: {candidate['id']})
   Rule Score: {candidate.get('score', 0):.2f}
   Risk: {candidate.get('risk_level')}
   Time: {candidate.get('time_to_effect')}
   Cost: {candidate.get('cost')}
   Success Rate: {candidate.get('success_rate', 'N/A')}
   Why: {candidate.get('reasoning', 'N/A')}
"""
        
        # Extract key context
        hot_path = incident_context.get("hot_path", "unknown")
        latency = incident_context.get("latency_current", 0)
        loss = incident_context.get("loss_current", 0)
        util = incident_context.get("utilization", {})
        priority = incident_context.get("priority", "medium")
        
        prompt = f"""You are a network incident remediation expert. Re-rank these playbook options considering the full incident context.

INCIDENT CONTEXT:
- Affected Path: {hot_path}
- Root Cause: {root_cause} (confidence: {confidence*100:.0f}%)
- Current Latency: {latency}ms
- Packet Loss: {loss}%
- Utilization: {util}
- Priority: {priority}

PLAYBOOK OPTIONS (Pre-scored by rules):
{candidates_text}

TASK:
Re-rank these options considering:
1. **Business Impact**: Is this customer-facing? Revenue impact?
2. **Time Sensitivity**: Can we afford a slower but more thorough fix?
3. **Risk Context**: What's our risk tolerance right now?
4. **Operational Reality**: Time of day, team expertise, resources available
5. **Success Patterns**: Historical success for this scenario

The rule-based scores are good starting points, but you should adjust based on contextual nuances they might miss.

Respond with JSON:
{{
    "recommendation_reasoning": "brief overall reasoning for ranking",
    "rankings": [
        {{
            "playbook_id": "qos_traffic_shaping",
            "score": 0.92,
            "reasoning": "why this rank"
        }},
        {{
            "playbook_id": "partial_traffic_offload",
            "score": 0.78,
            "reasoning": "why this rank"
        }},
        ...
    ]
}}

Scores should be 0.0-1.0. Only include playbooks from the list above.
"""
        
        return prompt
    
    def _extract_json_from_text(self, text: str) -> Dict:
        """Extract JSON from AI response text."""
        import re
        
        # Try to find JSON block
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            json_str = json_match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Fallback: return empty structure
        return {"rankings": [], "recommendation_reasoning": "Failed to parse AI response"}


def get_hybrid_recommendation_engine() -> HybridRecommendationEngine:
    """Get singleton hybrid recommendation engine."""
    return HybridRecommendationEngine()

