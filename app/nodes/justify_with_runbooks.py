"""
Node: Enhance candidates with explanations from runbook corpus (optional).
"""

import os
from app.models import IncidentState


def justify_with_runbooks(state: IncidentState) -> IncidentState:
    """
    Add explanation text to candidates based on runbook corpus.
    
    This is an optional node that performs simple text matching
    to find relevant runbook content for each remediation option.
    
    Args:
        state: Current incident state with candidates
        
    Returns:
        Updated state with explanations added to candidates
    """
    if state.error or not state.candidates:
        return state
    
    try:
        # Load runbook content
        runbooks_dir = os.path.join(os.path.dirname(__file__), "..", "runbooks")
        runbook_content = {}
        
        if os.path.exists(runbooks_dir):
            for filename in os.listdir(runbooks_dir):
                if filename.endswith('.txt'):
                    filepath = os.path.join(runbooks_dir, filename)
                    with open(filepath, 'r') as f:
                        runbook_content[filename] = f.read()
        
        # Simple keyword matching to attach explanations
        for candidate in state.candidates:
            explanation_parts = []
            
            # Search for relevant content based on candidate kind
            keywords = [candidate.kind, candidate.id]
            
            for runbook_name, content in runbook_content.items():
                for keyword in keywords:
                    if keyword.lower() in content.lower():
                        # Extract a relevant snippet (first 200 chars)
                        idx = content.lower().index(keyword.lower())
                        start = max(0, idx - 50)
                        end = min(len(content), idx + 150)
                        snippet = content[start:end].strip()
                        explanation_parts.append(f"From {runbook_name}: ...{snippet}...")
                        break
            
            if explanation_parts:
                candidate.explanation = " | ".join(explanation_parts[:2])  # Limit to 2 snippets
            else:
                candidate.explanation = f"Standard {candidate.kind} remediation procedure"
        
    except Exception as e:
        # Don't fail the workflow if runbooks are unavailable
        pass
    
    return state

