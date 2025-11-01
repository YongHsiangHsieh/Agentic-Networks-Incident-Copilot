"""
Unit tests for the Incident Playbook Picker workflow.
"""

import json
import os
import pytest
from app.models import IncidentBundle, IncidentState
from app.graph import build_graph, run_graph_until


def load_test_incident(filename: str) -> IncidentBundle:
    """Load a test incident from JSON file."""
    test_dir = os.path.dirname(__file__)
    filepath = os.path.join(test_dir, filename)
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    return IncidentBundle(**data)


def test_basic_incident_flow():
    """
    Test basic incident without config change.
    Should result in congestion hypothesis and valid recommendation.
    """
    # Load test incident
    bundle = load_test_incident("test_incident_basic.json")
    
    # Create initial state
    initial_state = IncidentState(
        incident_id=bundle.incident_id,
        bundle=bundle
    )
    
    # Build and run graph
    graph = build_graph(include_justification=False)
    final_state = run_graph_until(graph, initial_state, stop_at="policy_gate")
    
    # Assertions
    assert final_state.error is None, f"Workflow failed with error: {final_state.error}"
    
    # Check signals were computed
    assert final_state.signals is not None
    assert "delta_latency_ms" in final_state.signals
    assert "util_peak" in final_state.signals
    
    # Check hypothesis
    assert final_state.hypothesis is not None
    assert final_state.hypothesis["cause"] == "congestion"
    assert final_state.hypothesis["confidence"] >= 0.6
    
    # Check candidates
    assert final_state.candidates is not None
    assert len(final_state.candidates) >= 2  # Should have multiple options
    
    # Check policy verdicts
    assert final_state.policy_verdicts is not None
    assert len(final_state.policy_verdicts) > 0
    
    # Check recommendation exists
    assert final_state.recommendation is not None
    assert final_state.recommendation.policy_verdict["ok"] is True


def test_configchange_incident():
    """
    Test incident with recent config change.
    Should detect config change correlation.
    """
    # Load test incident with config change
    bundle = load_test_incident("test_incident_configchange.json")
    
    # Create initial state
    initial_state = IncidentState(
        incident_id=bundle.incident_id,
        bundle=bundle
    )
    
    # Build and run graph
    graph = build_graph(include_justification=False)
    final_state = run_graph_until(graph, initial_state, stop_at="policy_gate")
    
    # Assertions
    assert final_state.error is None
    
    # Check change correlation
    assert final_state.change_context is not None
    assert final_state.change_context["recent_change"] is True
    assert len(final_state.change_context["events"]) > 0
    
    # Hypothesis should note config issue
    assert final_state.hypothesis is not None
    # Could be primary or alternate cause
    assert (final_state.hypothesis["cause"] == "config_regression" or
            "alternate_cause" in final_state.hypothesis)


def test_policy_failure_scenario():
    """
    Test incident where policy constraints prevent recommendation.
    Should have candidates but no passing recommendation.
    """
    # Load test incident with strict policy
    bundle = load_test_incident("test_incident_policy_fail.json")
    
    # Create initial state
    initial_state = IncidentState(
        incident_id=bundle.incident_id,
        bundle=bundle
    )
    
    # Build and run graph
    graph = build_graph(include_justification=False)
    final_state = run_graph_until(graph, initial_state, stop_at="policy_gate")
    
    # Assertions
    assert final_state.error is None
    
    # Should have candidates
    assert final_state.candidates is not None
    assert len(final_state.candidates) > 0
    
    # Should have policy verdicts
    assert final_state.policy_verdicts is not None
    
    # Check if at least one candidate fails policy
    has_failure = False
    for verdict in final_state.policy_verdicts:
        if not verdict["verdict"]["ok"]:
            has_failure = True
            assert len(verdict["verdict"]["reasons"]) > 0
    
    # In this strict policy scenario, burst should be too expensive
    # and other options may exceed latency target
    assert has_failure, "Expected at least one policy failure"


def test_full_workflow_with_artifacts():
    """
    Test complete workflow including plan synthesis and artifact generation.
    """
    # Load test incident
    bundle = load_test_incident("test_incident_basic.json")
    
    # Create initial state
    initial_state = IncidentState(
        incident_id=bundle.incident_id,
        bundle=bundle
    )
    
    # Build and run complete graph
    graph = build_graph(include_justification=False)
    final_state = graph.invoke(initial_state)
    
    # Assertions
    assert final_state.error is None or final_state.recommendation is not None
    
    if final_state.recommendation:
        # Should have plan
        assert final_state.plan is not None
        assert "plan_json" in final_state.plan
        assert "rollback_tag" in final_state.plan
        assert bundle.incident_id in final_state.plan["rollback_tag"]
        
        # Should have artifacts
        assert final_state.artifacts is not None


def test_candidates_ranked_by_latency():
    """
    Test that candidates are ranked by predicted latency.
    """
    bundle = load_test_incident("test_incident_basic.json")
    
    initial_state = IncidentState(
        incident_id=bundle.incident_id,
        bundle=bundle
    )
    
    graph = build_graph(include_justification=False)
    final_state = run_graph_until(graph, initial_state, stop_at="policy_gate")
    
    assert final_state.candidates is not None
    assert len(final_state.candidates) >= 2
    
    # Check that candidates are sorted by latency
    latencies = [c.pred_latency_ms for c in final_state.candidates]
    assert latencies == sorted(latencies), "Candidates should be sorted by latency"


def test_simulator_projections():
    """
    Test that simulator produces reasonable projections.
    """
    bundle = load_test_incident("test_incident_basic.json")
    
    initial_state = IncidentState(
        incident_id=bundle.incident_id,
        bundle=bundle
    )
    
    graph = build_graph(include_justification=False)
    final_state = run_graph_until(graph, initial_state, stop_at="policy_gate")
    
    # All candidates should predict improvement
    baseline_latency = final_state.signals["baseline_latency_ms"]
    current_latency = final_state.signals["current_latency_ms"]
    
    for candidate in final_state.candidates:
        # Predicted latency should be less than current
        assert candidate.pred_latency_ms < current_latency, \
            f"Candidate {candidate.id} should improve latency"
        
        # Should be >= baseline (can't be better than normal)
        assert candidate.pred_latency_ms >= baseline_latency * 0.9, \
            f"Candidate {candidate.id} prediction should be reasonable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

