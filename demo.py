#!/usr/bin/env python
"""
Demo script for Incident Playbook Picker.

This script demonstrates the complete workflow:
1. Start the API (user must do this manually)
2. Load sample incidents
3. Diagnose each incident
4. Apply recommended remediation
5. Display results and artifacts

Usage:
    python demo.py
"""

import json
import time
import requests
from pathlib import Path


API_BASE = "http://localhost:8000"
TESTS_DIR = Path("tests")


def check_server():
    """Check if the API server is running."""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def load_incident(filename: str) -> dict:
    """Load an incident from JSON file."""
    filepath = TESTS_DIR / filename
    with open(filepath, 'r') as f:
        return json.load(f)


def diagnose_incident(incident_data: dict):
    """Call the diagnose_issue endpoint."""
    print(f"\n{'='*70}")
    print(f"DIAGNOSING INCIDENT: {incident_data['incident_id']}")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    response = requests.post(
        f"{API_BASE}/diagnose_issue",
        json=incident_data
    )
    elapsed = time.time() - start_time
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None
    
    result = response.json()
    
    # Display hypothesis
    hypothesis = result.get('hypothesis', {})
    print(f"🔍 ROOT CAUSE ANALYSIS:")
    print(f"   Cause: {hypothesis.get('cause', 'unknown')}")
    print(f"   Confidence: {hypothesis.get('confidence', 0)*100:.1f}%")
    print(f"   Details: {hypothesis.get('details', 'N/A')}")
    
    # Display candidates
    candidates = result.get('candidates', [])
    print(f"\n📋 REMEDIATION OPTIONS ({len(candidates)} available):")
    for i, candidate in enumerate(candidates, 1):
        verdict = candidate.get('policy_verdict', {})
        status = "✅ PASS" if verdict.get('ok') else "❌ FAIL"
        print(f"\n   {i}. {candidate['id']} [{status}]")
        print(f"      Type: {candidate['kind']}")
        print(f"      ETA: {candidate['eta_minutes']} minutes")
        print(f"      Predicted Latency: {candidate['pred_latency_ms']:.1f} ms")
        print(f"      Predicted Loss: {candidate['pred_loss_pct']:.2f}%")
        print(f"      Risk: {candidate['risk']}")
        print(f"      Cost: €{candidate['euro_delta']:.2f}/hr")
        if not verdict.get('ok'):
            print(f"      ⚠️  Reasons: {', '.join(verdict.get('reasons', []))}")
    
    # Display recommendation
    recommendation = result.get('recommendation')
    if recommendation:
        print(f"\n⭐ RECOMMENDED ACTION:")
        print(f"   {recommendation['id']} - {recommendation['kind']}")
    else:
        print(f"\n⚠️  NO VALID RECOMMENDATION (all options failed policy)")
    
    print(f"\n⏱️  Diagnosis completed in {elapsed:.3f} seconds")
    
    return result


def apply_remediation(incident_id: str, option_id: str):
    """Call the apply_option endpoint."""
    print(f"\n{'='*70}")
    print(f"APPLYING REMEDIATION")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    response = requests.post(
        f"{API_BASE}/apply_option",
        json={
            "incident_id": incident_id,
            "option_id": option_id
        }
    )
    elapsed = time.time() - start_time
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None
    
    result = response.json()
    
    # Display plan
    plan = result.get('plan', {})
    plan_json = plan.get('plan_json', {})
    print(f"📝 DEPLOYMENT PLAN:")
    print(f"   Version: {plan_json.get('version')}")
    print(f"   Action: {plan_json.get('action')}")
    print(f"   Rollback Tag: {plan.get('rollback_tag')}")
    print(f"   Duration: {plan_json.get('estimated_duration_minutes')} minutes")
    print(f"   Risk Level: {plan_json.get('risk_level')}")
    
    print(f"\n   Implementation Steps:")
    for i, step in enumerate(plan_json.get('steps', []), 1):
        print(f"      {i}. {step}")
    
    # Display artifacts
    artifacts = result.get('artifacts', {})
    print(f"\n📊 GENERATED ARTIFACTS:")
    print(f"   Chart: {artifacts.get('chart_png', 'N/A')}")
    print(f"   One-pager: {artifacts.get('one_pager', 'N/A')}")
    
    print(f"\n⏱️  Remediation applied in {elapsed:.3f} seconds")
    
    return result


def main():
    """Run the demo."""
    print("\n" + "="*70)
    print("  INCIDENT PLAYBOOK PICKER - DEMO")
    print("="*70)
    
    # Check server
    if not check_server():
        print("\n❌ ERROR: API server is not running!")
        print("\nPlease start the server first:")
        print("   uvicorn app.main:app --reload")
        print("\nThen run this demo again.")
        return
    
    print("\n✅ API server is running")
    
    # Demo incidents
    incidents = [
        ("test_incident_basic.json", "Basic Congestion"),
        ("test_incident_configchange.json", "Config Change"),
    ]
    
    for filename, description in incidents:
        print(f"\n\n{'#'*70}")
        print(f"# DEMO: {description}")
        print(f"{'#'*70}")
        
        try:
            # Load incident
            incident_data = load_incident(filename)
            
            # Diagnose
            diagnosis = diagnose_incident(incident_data)
            if not diagnosis:
                continue
            
            # Apply recommendation if available
            recommendation = diagnosis.get('recommendation')
            if recommendation:
                time.sleep(1)  # Brief pause for readability
                apply_result = apply_remediation(
                    incident_data['incident_id'],
                    recommendation['id']
                )
                
                if apply_result:
                    one_pager = apply_result['artifacts'].get('one_pager')
                    if one_pager:
                        print(f"\n💡 TIP: View the detailed report:")
                        print(f"   open {one_pager}")
        
        except Exception as e:
            print(f"\n❌ Error in demo: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\n\n{'='*70}")
    print("  DEMO COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("  1. Review generated artifacts in the artifacts/ directory")
    print("  2. Open the HTML one-pagers in a browser")
    print("  3. Examine the timeseries charts")
    print("  4. Try modifying test incidents or creating new ones")
    print("\nFor API documentation, visit: http://localhost:8000/docs")
    print()


if __name__ == "__main__":
    main()

