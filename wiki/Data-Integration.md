# Data Integration

Summarizes `DATA_INTEGRATION_GUIDE.md` with production pathways.

## Approaches
- Push-based (webhooks from PagerDuty/alerts; fetch metrics from Prometheus)
- Pull-based (poll metrics periodically and detect anomalies)
- Hybrid (MCP tools that fetch live data upon request)

## Sources
- Metrics: Prometheus, Datadog
- Logs/Events: Splunk
- Network: SNMP, NetFlow
- Incident Mgmt: PagerDuty, ServiceNow

## Recommendation
- Hackathon/demo: simulated live metrics via MCP tool
- Production: integrate Prometheus first; add PagerDuty webhook

See also: [API Reference](API-Reference.md), [MCP Tools](MCP-Tools.md).

