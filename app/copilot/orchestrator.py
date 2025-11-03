"""
Main copilot orchestration - ties all agents together into a cohesive system.
"""

from typing import Dict, List, Optional
from app.agents.root_cause_agent import RootCauseAgent, get_agent as get_diagnosis_agent
from app.agents.recommendation_engine import RecommendationEngine, get_recommendation_engine
from app.agents.command_generator import CommandGenerator, get_command_generator
from app.agents.rca_generator import RCAGenerator, get_generator as get_rca_generator
from app.models import IncidentData


class IncidentCopilot:
    """
    Complete AI Copilot for Network Incident Response.
    
    Provides:
    1. Diagnosis - Identify root cause
    2. Recommendations - Rank remediation options
    3. Commands - Generate safe CLI commands
    4. Documentation - Generate RCA reports
    """
    
    def __init__(self):
        self.diagnosis_agent = get_diagnosis_agent()
        self.recommender = get_recommendation_engine()
        self.command_gen = get_command_generator()
        self.rca_gen = get_rca_generator()
    
    def diagnose(self, incident_data: dict) -> Dict:
        """
        Analyze incident and identify root cause.
        
        Args:
            incident_data: Raw incident data with metrics, paths, etc.
        
        Returns:
            Dict with root_cause, confidence, evidence, severity
        """
        # Build incident state for diagnosis agent
        state = self._build_diagnosis_state(incident_data)
        
        # Run diagnosis
        diagnosis = self.diagnosis_agent.analyze(state)
        
        return {
            "root_cause": diagnosis.get("hypothesis", "Unknown"),
            "confidence": diagnosis.get("confidence", 0.5),
            "evidence": diagnosis.get("evidence", []),
            "severity": self._assess_severity(incident_data),
            "diagnosis_details": diagnosis,
        }
    
    def recommend(self, diagnosis: Dict, incident_context: dict, top_n: int = 3) -> Dict:
        """
        Suggest ranked remediation options based on diagnosis.
        
        Args:
            diagnosis: Output from diagnose() method
            incident_context: Additional context for recommendation
            top_n: Number of top recommendations to return
        
        Returns:
            Dict with ranked options and reasoning
        """
        return self.recommender.recommend(
            root_cause=diagnosis["root_cause"],
            confidence=diagnosis["confidence"],
            incident_context=incident_context,
            top_n=top_n
        )
    
    def generate_commands(
        self,
        playbook_id: str,
        incident_context: dict,
        include_verification: bool = True,
        include_rollback: bool = True
    ) -> Dict:
        """
        Generate safe, personalized CLI commands for a specific playbook.
        
        Args:
            playbook_id: ID of the playbook to use
            incident_context: Incident-specific data
            include_verification: Include verification steps
            include_rollback: Include rollback procedure
        
        Returns:
            Dict with commands, verification, rollback, warnings
        """
        return self.command_gen.generate(
            playbook_id=playbook_id,
            incident_context=incident_context,
            include_verification=include_verification,
            include_rollback=include_rollback
        )
    
    def generate_rca(self, incident_data: IncidentData) -> str:
        """
        Generate comprehensive RCA report.
        
        Args:
            incident_data: Complete incident data
        
        Returns:
            RCA markdown string
        """
        result = self.rca_gen.generate(incident_data)
        return result['markdown']
    
    def full_workflow(self, incident_data: dict) -> Dict:
        """
        Complete copilot workflow: Diagnose → Recommend → Ready to Execute
        
        This is the main entry point for the full copilot experience.
        
        Args:
            incident_data: Raw incident data
        
        Returns:
            Complete copilot analysis with diagnosis, recommendations, and next steps
        """
        # Step 1: Diagnose
        diagnosis = self.diagnose(incident_data)
        
        # Step 2: Get recommendations
        recommendations = self.recommend(diagnosis, incident_data)
        
        # Step 3: Prepare summary
        return {
            "diagnosis": diagnosis,
            "recommendations": recommendations,
            "next_steps": self._format_next_steps(diagnosis, recommendations),
            "can_generate_rca": True,
        }
    
    def _build_diagnosis_state(self, incident_data: dict) -> dict:
        """Build state dict for diagnosis agent"""
        # Extract metrics
        metrics = incident_data.get("metrics", {})
        
        # Get latency data
        latency_ms = metrics.get("latency_ms", [45.0])
        if isinstance(latency_ms, list) and latency_ms:
            latency_current = latency_ms[-1]
            latency_baseline = sum(latency_ms[:len(latency_ms)//2]) / max(1, len(latency_ms)//2) if len(latency_ms) > 2 else 45.0
        else:
            latency_current = latency_ms if isinstance(latency_ms, (int, float)) else 45.0
            latency_baseline = 45.0
        
        # Get loss data
        loss_pct = metrics.get("loss_pct", [0.05])
        if isinstance(loss_pct, list) and loss_pct:
            loss_current = loss_pct[-1]
            loss_baseline = sum(loss_pct[:len(loss_pct)//2]) / max(1, len(loss_pct)//2) if len(loss_pct) > 2 else 0.05
        else:
            loss_current = loss_pct if isinstance(loss_pct, (int, float)) else 0.05
            loss_baseline = 0.05
        
        # Get utilization data
        util_pct = metrics.get("util_pct", {})
        
        # Build signals dict
        signals = {
            "latency_spike": latency_current > latency_baseline * 1.5,
            "loss_spike": loss_current > loss_baseline * 2,
            "high_util": any(u > 70 for u in util_pct.values()) if isinstance(util_pct, dict) else False,
        }
        
        # Build change context
        change_context = {
            "recent_changes": incident_data.get("actions_taken", []),
            "timestamp": incident_data.get("timestamp_start", ""),
        }
        
        return {
            "bundle": incident_data,
            "signals": signals,
            "change_context": change_context,
            "metrics": metrics,
        }
    
    def _assess_severity(self, incident_data: dict) -> str:
        """Assess incident severity based on metrics"""
        metrics = incident_data.get("metrics", {})
        
        # Get current metrics
        latency_ms = metrics.get("latency_ms", [45])
        loss_pct = metrics.get("loss_pct", [0.05])
        
        current_latency = latency_ms[-1] if isinstance(latency_ms, list) else latency_ms
        current_loss = loss_pct[-1] if isinstance(loss_pct, list) else loss_pct
        
        # Assess severity
        if current_latency > 200 or current_loss > 5:
            return "CRITICAL"
        elif current_latency > 100 or current_loss > 1:
            return "HIGH"
        elif current_latency > 60 or current_loss > 0.5:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _format_next_steps(self, diagnosis: Dict, recommendations: Dict) -> List[str]:
        """Format actionable next steps for the engineer"""
        steps = []
        
        # Step 1: Review diagnosis
        steps.append(
            f"1. Review diagnosis: {diagnosis['root_cause']} "
            f"(confidence: {int(diagnosis['confidence'] * 100)}%)"
        )
        
        # Step 2: Choose recommendation
        if recommendations.get("options"):
            top_option = recommendations["options"][0]
            steps.append(
                f"2. Recommended action: '{top_option['name']}' "
                f"(risk: {top_option['risk_level']}, impact: {top_option['estimated_impact']})"
            )
            steps.append(
                f"3. To see commands: ask 'Show me commands for {top_option['id']}'"
            )
        
        # Step 3: Execution
        steps.append("4. Review commands carefully before executing")
        steps.append("5. Execute commands and monitor metrics")
        steps.append("6. Generate RCA report when incident is resolved")
        
        return steps


# Singleton instance
_copilot_instance: Optional[IncidentCopilot] = None


def get_copilot() -> IncidentCopilot:
    """Get singleton instance of IncidentCopilot"""
    global _copilot_instance
    if _copilot_instance is None:
        _copilot_instance = IncidentCopilot()
    return _copilot_instance

