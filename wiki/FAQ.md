# FAQ

## Why not fully automate remediation?
High risk and low trust in production. Human approvals keep safety and accountability.

## Why AWS Bedrock + Claude?
IAM security, strong reasoning, low-cost Haiku tier, native AWS integration.

## What if AI fails or is unavailable?
Graceful fallback to rule-based logic in diagnosis and recommendations.

## How is safety enforced for commands?
Templates, parameter validation, verification steps, and explicit rollback.

## Where does data come from in production?
Integrate monitoring (Prometheus, Datadog) and incident mgmt (PagerDuty) per [Data Integration](Data-Integration.md).

