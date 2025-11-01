"""
Chart and report generation for incident artifacts.
"""

import os
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from jinja2 import Template
from datetime import datetime


def render_timeseries_chart(
    before_latency: list,
    after_latency: list,
    before_loss: list,
    after_loss: list,
    output_path: str
) -> str:
    """
    Generate before/after comparison chart for latency and loss metrics.
    
    Args:
        before_latency: List of latency values before remediation
        after_latency: List of latency values after remediation
        before_loss: List of loss percentages before remediation
        after_loss: List of loss percentages after remediation
        output_path: Path to save the PNG file
        
    Returns:
        Path to the saved chart
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Latency chart
    before_x = list(range(len(before_latency)))
    after_x = list(range(len(before_latency), len(before_latency) + len(after_latency)))
    
    ax1.plot(before_x, before_latency, 'r-', label='Before (Incident)', linewidth=2)
    ax1.plot(after_x, after_latency, 'g--', label='After (Projected)', linewidth=2)
    ax1.axvline(x=len(before_latency) - 0.5, color='orange', linestyle=':', 
                linewidth=2, label='Remediation Applied')
    ax1.set_ylabel('Latency (ms)', fontsize=12)
    ax1.set_title('Network Latency: Before vs After Remediation', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    # Loss chart
    ax2.plot(before_x, before_loss, 'r-', label='Before (Incident)', linewidth=2)
    ax2.plot(after_x, after_loss, 'g--', label='After (Projected)', linewidth=2)
    ax2.axvline(x=len(before_loss) - 0.5, color='orange', linestyle=':', 
                linewidth=2, label='Remediation Applied')
    ax2.set_xlabel('Time (samples)', fontsize=12)
    ax2.set_ylabel('Packet Loss (%)', fontsize=12)
    ax2.set_title('Packet Loss: Before vs After Remediation', fontsize=14, fontweight='bold')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_path


def render_one_pager(
    incident_id: str,
    hypothesis: dict,
    recommendation: dict,
    plan: dict,
    euro_spent: float,
    euro_avoided: float,
    time_to_diagnosis_sec: float,
    time_to_restore_min: float,
    output_path: str
) -> str:
    """
    Generate HTML one-pager report for the incident.
    
    Args:
        incident_id: Unique incident identifier
        hypothesis: Root cause hypothesis dict
        recommendation: Selected remediation option dict
        plan: Generated plan dict
        euro_spent: Cost of remediation
        euro_avoided: SLA penalty avoided
        time_to_diagnosis_sec: Time taken to diagnose
        time_to_restore_min: Estimated time to restore service
        output_path: Path to save the HTML file
        
    Returns:
        Path to the saved report
    """
    template_str = """
<!DOCTYPE html>
<html>
<head>
    <title>Incident Report: {{ incident_id }}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1000px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin: 20px 0;
        }
        .metric-card {
            background: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            border-left: 4px solid #3498db;
        }
        .metric-card h3 {
            margin: 0 0 10px 0;
            color: #7f8c8d;
            font-size: 14px;
            text-transform: uppercase;
        }
        .metric-card .value {
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
        }
        .success {
            color: #27ae60;
        }
        .warning {
            color: #f39c12;
        }
        .info-box {
            background: #e8f4f8;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }
        .cost-summary {
            background: #d5f4e6;
            border-left: 4px solid #27ae60;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
        }
        .cost-summary h3 {
            margin: 0 0 10px 0;
            color: #27ae60;
        }
        pre {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 13px;
        }
        .timestamp {
            color: #7f8c8d;
            font-size: 14px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #34495e;
            color: white;
        }
        tr:hover {
            background: #f5f5f5;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Incident Playbook Picker Report</h1>
        <p class="timestamp">Generated: {{ timestamp }}</p>
        
        <div class="info-box">
            <strong>Incident ID:</strong> {{ incident_id }}
        </div>
        
        <h2>Root Cause Analysis</h2>
        <p><strong>Hypothesis:</strong> {{ hypothesis.cause }}</p>
        <p><strong>Confidence:</strong> {{ (hypothesis.confidence * 100)|round(1) }}%</p>
        
        <h2>Recommended Remediation</h2>
        <table>
            <tr>
                <th>Option ID</th>
                <th>Type</th>
                <th>ETA</th>
                <th>Risk</th>
            </tr>
            <tr>
                <td>{{ recommendation.id }}</td>
                <td>{{ recommendation.kind }}</td>
                <td>{{ recommendation.eta_minutes }} minutes</td>
                <td>{{ recommendation.risk }}</td>
            </tr>
        </table>
        
        <h2>Performance Metrics</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <h3>Time to Diagnosis</h3>
                <div class="value success">{{ time_to_diagnosis_sec|round(2) }}s</div>
            </div>
            <div class="metric-card">
                <h3>Time to Restore</h3>
                <div class="value">{{ time_to_restore_min|round(1) }} min</div>
            </div>
            <div class="metric-card">
                <h3>Predicted Latency</h3>
                <div class="value">{{ recommendation.pred_latency_ms|round(1) }} ms</div>
            </div>
            <div class="metric-card">
                <h3>Predicted Loss</h3>
                <div class="value">{{ recommendation.pred_loss_pct|round(2) }}%</div>
            </div>
        </div>
        
        <div class="cost-summary">
            <h3>Financial Impact</h3>
            <p><strong>Remediation Cost:</strong> €{{ euro_spent|round(2) }}/hr</p>
            <p><strong>SLA Penalty Avoided:</strong> €{{ euro_avoided|round(2) }}</p>
            <p><strong>Net Savings:</strong> <span class="success">€{{ (euro_avoided - euro_spent)|round(2) }}</span></p>
        </div>
        
        <h2>Deployment Plan</h2>
        <p><strong>Rollback Tag:</strong> <code>{{ plan.rollback_tag }}</code></p>
        <pre>{{ plan.plan_json|tojson(indent=2) }}</pre>
        
        <h2>Next Steps</h2>
        <ol>
            <li>Review and approve the remediation plan</li>
            <li>Execute deployment via automation pipeline</li>
            <li>Monitor metrics for {{ recommendation.eta_minutes }} minutes</li>
            <li>Verify latency returns to acceptable levels</li>
            <li>Document incident for post-mortem analysis</li>
        </ol>
    </div>
</body>
</html>
    """
    
    template = Template(template_str)
    
    html_content = template.render(
        incident_id=incident_id,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        hypothesis=hypothesis,
        recommendation=recommendation,
        plan=plan,
        euro_spent=euro_spent,
        euro_avoided=euro_avoided,
        time_to_diagnosis_sec=time_to_diagnosis_sec,
        time_to_restore_min=time_to_restore_min
    )
    
    with open(output_path, 'w') as f:
        f.write(html_content)
    
    return output_path

