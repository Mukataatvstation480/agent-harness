# Demo: public-search-fallback

**Description**: No-key public search fallback (DuckDuckGo/SearXNG if available) + deterministic synthesis.

**Query**: Compare Redis, Valkey, and Memcached for low-latency caching in a high-traffic API.

**Mission**: research

**Evidence records**: 6

**Citations**: 6

**Live agent**: success=False calls=0

**Value index**: 76.29

---

# Decision Guide

## Request

Compare Redis, Valkey, and Memcached for low-latency caching in a high-traffic API.

## Deliverable

This run collected evidence relevant to the request and packaged it into a reviewable deliverable. The answer should be grounded in the sources below rather than generated from general knowledge alone.

## Evidence

- [Human Override Policy for Regulated Support Copilots](internal://fintech/human-override-policy) — Customer-facing copilots in regulated queues need explicit operator takeover conditions, SLA limits, and audit logs for overrides.
- [Workflow Rollout Scorecard](internal://enterprise/workflow-rollout-scorecard) — Enterprise rollouts should track workflow time saved, fallback rate, escalation rate, and team adoption before widening scope.
- [tau-bench](https://github.com/sierra-research/tau-bench) — Enterprise-oriented benchmark for realistic tool-using agent tasks and long-horizon workflows.
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) — Baseline framing for govern, map, measure, and manage controls in AI deployments.
- [Audit Readiness Checklist for AI Service Launches](internal://fintech/audit-readiness-checklist) — Launch packets need retained traces, policy versioning, evidence retention, and reviewer attribution before expansion.
- [Evidence Packet Template](internal://cross/evidence-packet-template) — A release packet should combine quantitative metrics, control decisions, citations, unresolved risks, and expansion triggers in one artifact.

## Next Actions

- Understand goal, constraints, and desired end state.
- Collect external resources.
- Build evidence dossier.
- Discover relevant tools.
- Inspect skill priors.
- Analyze task.

## Runtime Notes

- security preflight: allow (score=0.00)
- recipe: none
- discovered tools: evidence_dossier_builder, api_market_discover, api_skill_portfolio_optimizer, ecosystem_provider_radar, tool_search
- api_market_discover: OK (1.0ms)
- api_skill_portfolio_optimizer: OK (2.3ms)
- task_graph_builder: OK (493.1ms)
- external_resource_hub: OK (2.8ms)

## Sources

- internal://fintech/human-override-policy
- internal://enterprise/workflow-rollout-scorecard
- https://github.com/sierra-research/tau-bench
- https://www.nist.gov/itl/ai-risk-management-framework
