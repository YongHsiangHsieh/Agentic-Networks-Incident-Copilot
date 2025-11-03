"""
Safe command generation with parameter substitution and validation.
"""

import re
from typing import Dict, List
from datetime import datetime
from app.playbooks.playbook_library import Playbook, get_playbook_by_id


class CommandGenerator:
    """Generates safe, personalized CLI commands from playbook templates"""
    
    def __init__(self):
        self.dangerous_patterns = [
            r"rm\s+-rf",
            r"del\s+/f",
            r"format\s+",
            r"erase\s+nvram",
            r"write\s+erase",
        ]
    
    def generate(
        self,
        playbook_id: str,
        incident_context: dict,
        include_verification: bool = True,
        include_rollback: bool = True
    ) -> Dict:
        """
        Generate personalized, safe CLI commands from a playbook.
        
        Args:
            playbook_id: ID of the playbook to use
            incident_context: Incident-specific data for parameter substitution
            include_verification: Include verification steps
            include_rollback: Include rollback procedure
        
        Returns:
            Dict with commands, verification, rollback, and warnings
        """
        playbook = get_playbook_by_id(playbook_id)
        if not playbook:
            return {"error": f"Playbook '{playbook_id}' not found"}
        
        # Build parameter dictionary
        params = self._build_parameters(incident_context, playbook)
        
        # Substitute parameters in command template
        try:
            commands = self._substitute_parameters(playbook.commands_template, params)
        except KeyError as e:
            return {
                "error": f"Missing required parameter: {e}",
                "required_parameters": self._extract_placeholders(playbook.commands_template),
                "provided_parameters": list(params.keys()),
            }
        
        # Validate safety
        safety_warnings = self._validate_safety(commands, playbook)
        
        # Build verification commands if requested
        verification = None
        if include_verification:
            verification = self._format_verification(playbook, params)
        
        # Build rollback commands if requested
        rollback = None
        if include_rollback:
            rollback = self._substitute_parameters(playbook.rollback_procedure, params)
        
        return {
            "playbook_id": playbook_id,
            "playbook_name": playbook.name,
            "risk_level": playbook.risk_level,
            "time_to_effect": playbook.time_to_effect,
            "estimated_impact": playbook.estimated_impact,
            "commands": commands,
            "verification": verification,
            "rollback": rollback,
            "safety_warnings": safety_warnings,
            "prerequisites": playbook.prerequisites,
            "success_indicators": playbook.success_indicators,
            "estimated_execution_time": self._estimate_execution_time(playbook),
        }
    
    def _build_parameters(self, context: dict, playbook: Playbook) -> Dict:
        """Build parameter dictionary from incident context"""
        params = {}
        
        # Standard parameters
        params["timestamp"] = datetime.now().strftime("%Y%m%d-%H%M%S")
        params["hot_path"] = context.get("hot_path", "UNKNOWN_PATH")
        
        # Parse hot_path to extract router names
        if "-" in params["hot_path"]:
            parts = params["hot_path"].split("-")
            params["router_source"] = parts[0] if len(parts) > 0 else "RouterA"
            params["router_dest"] = parts[1] if len(parts) > 1 else "RouterB"
        else:
            params["router_source"] = "RouterA"
            params["router_dest"] = "RouterB"
        
        # Metrics
        metrics = context.get("metrics", {})
        
        # Latency parameters
        latency_current = context.get("latency_current", metrics.get("latency_ms", [0])[-1] if isinstance(metrics.get("latency_ms"), list) else 0)
        latency_baseline = context.get("latency_baseline", 45)
        params["current_latency"] = int(latency_current)
        params["expected_latency"] = int(latency_baseline)
        
        # Loss parameters
        loss_current = context.get("loss_current", metrics.get("loss_pct", [0])[-1] if isinstance(metrics.get("loss_pct"), list) else 0)
        loss_baseline = context.get("loss_baseline", 0.05)
        params["current_loss"] = round(loss_current, 2)
        params["expected_loss"] = round(loss_baseline, 2)
        
        # Utilization
        util = context.get("utilization", metrics.get("util_pct", {}))
        if isinstance(util, dict):
            avg_util = sum(util.values()) / len(util.values()) if util else 50
        else:
            avg_util = util
        params["current_util"] = int(avg_util)
        
        # Interface and network parameters
        params["interface_id"] = context.get("interface_id", "GigabitEthernet0/0/1")
        params["destination_network"] = context.get("destination_network", "10.0.0.0/8")
        params["alternate_interface"] = context.get("alternate_interface", "GigabitEthernet0/0/2")
        params["alternate_next_hop"] = context.get("alternate_next_hop", "192.168.1.254")
        
        # Routing parameters
        params["asn"] = context.get("asn", "65000")
        params["routing_protocol"] = context.get("routing_protocol", "bgp")
        params["route_map_name"] = context.get("route_map_name", "EMERGENCY_REMAP")
        params["peer_ip"] = context.get("peer_ip", "192.168.1.1")
        params["higher_preference"] = context.get("higher_preference", "200")
        params["new_cost"] = context.get("new_cost", "10")
        params["prefix_list"] = context.get("prefix_list", "AFFECTED_ROUTES")
        
        # Config parameters
        params["backup_config_path"] = context.get("backup_config_path", "flash:backup-config.cfg")
        params["commit_id"] = context.get("commit_id", "1")
        params["change_timestamp"] = context.get("change_timestamp", "recent")
        params["changed_section"] = context.get("changed_section", "routing")
        params["affected_routes"] = context.get("affected_routes", "all")
        
        # Hardware parameters
        params["module_id"] = context.get("module_id", "1")
        params["suspected_component"] = context.get("suspected_component", "line card")
        params["alternate_path"] = context.get("alternate_path", "backup-path")
        
        # Capacity parameters
        params["circuit_id"] = context.get("circuit_id", "CIRCUIT-12345")
        params["current_bandwidth"] = context.get("current_bandwidth", "1Gbps")
        params["new_bandwidth"] = context.get("new_bandwidth", "10Gbps")
        params["new_bandwidth_kbps"] = context.get("new_bandwidth_kbps", "10000000")
        
        # Additional context
        params["destination_ip"] = context.get("destination_ip", "10.0.0.1")
        params["current_path"] = context.get("current_path", params["hot_path"])
        params["optimal_path"] = context.get("optimal_path", "optimized-path")
        
        return params
    
    def _substitute_parameters(self, template: str, params: Dict) -> str:
        """Replace {placeholders} with actual values"""
        result = template
        for key, value in params.items():
            placeholder = "{" + key + "}"
            result = result.replace(placeholder, str(value))
        return result
    
    def _extract_placeholders(self, template: str) -> List[str]:
        """Extract all {placeholder} names from template"""
        return re.findall(r'\{(\w+)\}', template)
    
    def _validate_safety(self, commands: str, playbook: Playbook) -> List[str]:
        """Check for potential safety issues"""
        warnings = []
        
        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, commands, re.IGNORECASE):
                warnings.append(f"⚠️ DANGER: Destructive command detected: {pattern}")
        
        # Warn on high-risk playbooks
        if playbook.risk_level in ["HIGH", "CRITICAL"]:
            warnings.append(f"⚠️ This playbook is {playbook.risk_level} risk. Review carefully before executing.")
        
        # Check for missing backups
        if "backup" not in commands.lower() and playbook.risk_level in ["MEDIUM", "HIGH", "CRITICAL"]:
            warnings.append("⚠️ No backup step found. Consider backing up configuration first.")
        
        # Check for write operations
        if "write memory" in commands.lower() or "write" in commands.lower():
            warnings.append("ℹ️ Commands will modify saved configuration (write memory)")
        
        return warnings if warnings else ["✅ No critical safety issues detected"]
    
    def _format_verification(self, playbook: Playbook, params: Dict) -> Dict:
        """Format verification steps with context"""
        return {
            "steps": playbook.verification_steps,
            "success_indicators": playbook.success_indicators,
            "what_to_check": f"Monitor for {playbook.time_to_effect}, expecting: {playbook.estimated_impact}",
        }
    
    def _estimate_execution_time(self, playbook: Playbook) -> str:
        """Estimate how long the commands take to execute"""
        # Execution time is usually much shorter than time_to_effect
        if "minute" in playbook.time_to_effect.lower():
            return "2-5 minutes to execute commands"
        elif "hour" in playbook.time_to_effect.lower():
            return "5-15 minutes to execute commands"
        return "5-10 minutes to execute commands"


def get_command_generator() -> CommandGenerator:
    """Get singleton instance of command generator"""
    return CommandGenerator()

