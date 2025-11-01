"""
Node: Correlate recent changes with incident timeline.
"""

from datetime import datetime, timedelta
from app.models import IncidentState


def correlate_changes(state: IncidentState) -> IncidentState:
    """
    Filter and correlate recent change events.
    
    Identifies changes within the last 10 minutes of the incident window
    and checks if they match hops in the hot path.
    
    Args:
        state: Current incident state
        
    Returns:
        Updated state with change_context populated
    """
    if state.error:
        return state
    
    try:
        bundle = state.bundle
        changes = bundle.changes
        
        # Parse window end time
        window = bundle.window
        end_ts_str = window.get("end_ts", "")
        
        # Simple correlation: check if any changes are recent
        # For demo purposes, consider changes in last 10 minutes as "recent"
        recent_change = False
        relevant_events = []
        
        if end_ts_str and changes:
            try:
                end_ts = datetime.fromisoformat(end_ts_str.replace('Z', '+00:00'))
                cutoff = end_ts - timedelta(minutes=10)
                
                for change in changes:
                    change_ts = datetime.fromisoformat(change.ts.replace('Z', '+00:00'))
                    if change_ts >= cutoff:
                        # Check if change scope matches any hop in hot_path
                        hot_path = bundle.hot_path
                        if change.scope in hot_path:
                            recent_change = True
                            relevant_events.append(change.model_dump())
            except (ValueError, AttributeError):
                # If timestamp parsing fails, just check if changes exist
                if changes:
                    recent_change = True
                    relevant_events = [c.model_dump() for c in changes]
        
        state.change_context = {
            "recent_change": recent_change,
            "events": relevant_events
        }
        
    except Exception as e:
        state.error = f"Error correlating changes: {str(e)}"
    
    return state

