"""
Intelligent recommendation engine that ranks remediation playbooks.
"""

from typing import List, Dict
from app.playbooks.playbook_library import ALL_PLAYBOOKS, Playbook, get_playbooks_for_root_cause


class RecommendationEngine:
    """Ranks remediation playbooks based on context and multiple factors"""
    
    def __init__(self):
        self.playbooks = ALL_PLAYBOOKS
        self.risk_scores = {"LOW": 1.0, "MEDIUM": 0.7, "HIGH": 0.4, "CRITICAL": 0.2}
        self.cost_scores = {"FREE": 1.0, "LOW": 0.9, "MEDIUM": 0.6, "HIGH": 0.3}
    
    def recommend(
        self,
        root_cause: str,
        confidence: float,
        incident_context: dict,
        top_n: int = 3
    ) -> Dict:
        """
        Returns ranked remediation options with detailed reasoning.
        
        Args:
            root_cause: Identified root cause (e.g., "congestion", "hardware_failure")
            confidence: Diagnosis confidence (0.0-1.0)
            incident_context: Incident details (metrics, paths, etc.)
            top_n: Number of top recommendations to return
        
        Returns:
            Dict with ranked options and reasoning
        """
        # Get relevant playbooks
        candidates = get_playbooks_for_root_cause(root_cause)
        
        # If no exact matches, use all playbooks but with lower scores
        if not candidates:
            candidates = self.playbooks.copy()
        
        # Score each playbook
        scored = []
        for playbook in candidates:
            score = self._score_playbook(playbook, root_cause, confidence, incident_context)
            scored.append({
                "playbook": playbook,
                "score": score,
                "reasoning": self._explain_score(playbook, score, root_cause, incident_context)
            })
        
        # Sort by score (descending)
        scored.sort(key=lambda x: x["score"], reverse=True)
        
        # Take top N
        top_recommendations = scored[:top_n]
        
        # Format response
        return {
            "root_cause": root_cause,
            "confidence": confidence,
            "recommended": top_recommendations[0]["playbook"].id if top_recommendations else None,
            "options": [
                {
                    "rank": idx + 1,
                    "id": rec["playbook"].id,
                    "name": rec["playbook"].name,
                    "description": rec["playbook"].description,
                    "risk_level": rec["playbook"].risk_level,
                    "time_to_effect": rec["playbook"].time_to_effect,
                    "estimated_impact": rec["playbook"].estimated_impact,
                    "cost": rec["playbook"].cost,
                    "score": round(rec["score"], 2),
                    "reasoning": rec["reasoning"],
                    "when_to_use": rec["playbook"].when_to_use,
                    "success_rate": f"{int(rec['playbook'].typical_success_rate * 100)}%",
                }
                for idx, rec in enumerate(top_recommendations)
            ],
            "total_candidates": len(candidates),
        }
    
    def _score_playbook(
        self,
        playbook: Playbook,
        root_cause: str,
        confidence: float,
        context: dict
    ) -> float:
        """
        Multi-factor scoring algorithm.
        
        Factors:
        1. Root cause match (40% weight)
        2. Risk level (25% weight)
        3. Time to effect (15% weight)
        4. Cost (10% weight)
        5. Historical success rate (10% weight)
        """
        score = 0.0
        
        # Factor 1: Root cause match (40%)
        root_cause_score = 0.0
        if root_cause.lower() in [rc.lower() for rc in playbook.root_causes]:
            root_cause_score = 1.0
        else:
            # Partial match for related causes
            if "congestion" in root_cause.lower() and "latency" in " ".join(playbook.root_causes).lower():
                root_cause_score = 0.5
        score += root_cause_score * 0.40
        
        # Factor 2: Risk level (25%) - prefer lower risk
        risk_score = self.risk_scores.get(playbook.risk_level, 0.5)
        score += risk_score * 0.25
        
        # Factor 3: Time to effect (15%) - prefer faster
        time_score = self._time_to_score(playbook.time_to_effect)
        score += time_score * 0.15
        
        # Factor 4: Cost (10%) - prefer cheaper
        cost_score = self.cost_scores.get(playbook.cost, 0.5)
        score += cost_score * 0.10
        
        # Factor 5: Historical success rate (10%)
        score += playbook.typical_success_rate * 0.10
        
        # Adjust based on confidence
        # If low confidence, further prefer low-risk options
        if confidence < 0.7:
            if playbook.risk_level in ["HIGH", "CRITICAL"]:
                score *= 0.7  # Penalize high-risk options when uncertain
        
        return score
    
    def _time_to_score(self, time_str: str) -> float:
        """Convert time string to score (faster = higher)"""
        time_lower = time_str.lower()
        
        if "minute" in time_lower:
            if "1" in time_lower or "2" in time_lower:
                return 1.0
            elif "5" in time_lower or "10" in time_lower:
                return 0.8
            elif "15" in time_lower or "30" in time_lower:
                return 0.6
        elif "hour" in time_lower:
            if "1" in time_lower or "2" in time_lower:
                return 0.4
            else:
                return 0.2
        
        return 0.5  # Default
    
    def _explain_score(
        self,
        playbook: Playbook,
        score: float,
        root_cause: str,
        context: dict
    ) -> str:
        """Generate human-readable explanation for the score"""
        reasons = []
        
        # Root cause match
        if root_cause.lower() in [rc.lower() for rc in playbook.root_causes]:
            reasons.append(f"✅ Directly addresses {root_cause}")
        else:
            reasons.append(f"⚠️ May help but not specific to {root_cause}")
        
        # Risk assessment
        if playbook.risk_level == "LOW":
            reasons.append("✅ Low risk, safe to apply")
        elif playbook.risk_level == "MEDIUM":
            reasons.append("⚠️ Medium risk, review carefully")
        else:
            reasons.append("⚠️ High risk, requires approval")
        
        # Time factor
        if "minute" in playbook.time_to_effect.lower() and any(x in playbook.time_to_effect for x in ["1", "2", "5"]):
            reasons.append("✅ Fast effect (< 10 minutes)")
        elif "hour" in playbook.time_to_effect.lower():
            reasons.append("⏰ Slower effect (hours)")
        
        # Cost factor
        if playbook.cost == "FREE":
            reasons.append("✅ No additional cost")
        elif playbook.cost == "HIGH":
            reasons.append("💰 High cost, budget approval needed")
        
        # Success rate
        if playbook.typical_success_rate >= 0.85:
            reasons.append(f"✅ High success rate ({int(playbook.typical_success_rate * 100)}%)")
        elif playbook.typical_success_rate < 0.75:
            reasons.append(f"⚠️ Moderate success rate ({int(playbook.typical_success_rate * 100)}%)")
        
        return " | ".join(reasons)


def get_recommendation_engine() -> RecommendationEngine:
    """Get singleton instance of recommendation engine"""
    return RecommendationEngine()

