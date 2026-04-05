# Agent Harness Studio

Agent Harness Studio turns one user request into an auditable, deliverable-first, and ecosystem-portable agent product.

## Task

Generate a deep research memo on how a general agent runtime should beat direct model answers on real tasks, including failure modes, design principles, and concrete runtime improvements.

## Primary Deliverable

Applied Research Delivery Operating Plan
Scenario: Launching an applied research platform that must ship product value while preserving experimental rigor.
Decision: go (all_quality_gates_passed)
Request: Generate a deep research memo on how a general agent runtime should beat direct model answers on real tasks, including failure modes, design principles, and concrete runtime improvements.
Operating Thesis:
- The proposal connects experiment design, evidence review, and product rollout into one repeatable system.
Business Summary:
- Move from isolated experiments to a governed release pipeline.
- Treat reproducibility and evidence history as launch requirements.
- Use staged release criteria so research wins can survive real production scrutiny.
- Evidence base: 12 records and 6 citations were injected into the launch packet.
Phased Rollout:
- Phase 1 - Evaluation Foundation: Stabilize scenario suites and quality gates., Define success metrics before scaling experiments., understand goal, constraints, and desired end state
- Phase 2 - Candidate Promotion: Run contenders through repeatable evaluation., Package evidence for decision review., collect external resources because external evidence is missing for this task
- Phase 3 - Production Rollout: Ship the winning candidate with monitoring hooks., Track post-launch drift against lab expectations., build evidence dossier because normalize the retrieved evidence into reviewable records
Expected Impact:
- Experiment throughput: release decision go with reason all_quality_gates_passed
- Evidence quality: completion score 1.00 and tool success 1.00
- Release confidence: internal value heuristic 76.9 and band gold
- Stakeholder trust: stakeholder packet ready for product, operations, and governance review
Critical Risks:
- Research signals look promising but do not translate to production operating constraints.
- Evaluation signals look promising but decision-makers cannot inspect the supporting evidence quickly enough.
- Experimental branches proliferate faster than governance can review them.
Evidence Citations:
- https://github.com/sierra-research/tau-bench
- https://modelcontextprotocol.io/specification/2025-06-18/architecture/index
- https://github.com/SWE-bench/SWE-bench
- internal://research/experiment-promotion-criteria
Execution Backbone:
- understand goal, constraints, and desired end state
- collect external resources because external evidence is missing for this task
- build evidence dossier because normalize the retrieved evidence into reviewable records
- discover relevant tools because task is open-ended and should inspect available operators first
- inspect skill priors because skill selection should come from explicit capability inspection
- analyze task because translate goal and constraints into an executable plan

## Task Context

A research and product organization needs one operating plan that can move experiments into production without losing reproducibility, auditability, or decision quality.

## Evidence References

- https://github.com/sierra-research/tau-bench
- https://modelcontextprotocol.io/specification/2025-06-18/architecture/index
- https://github.com/SWE-bench/SWE-bench
- internal://research/experiment-promotion-criteria
- https://huggingface.co/gaia-benchmark
- internal://cross/evidence-packet-template

## Deliverable Package

- Type: Research Mission Pack
- Primary deliverable: Research promotion packet with experiment rationale, evidence, and release criteria.
- Deliverable: Research Brief -> Hypothesis, operating thesis, and study implications.
- Deliverable: Delivery Readout -> Decision summary, release posture, and execution implications.
- Deliverable: Promotion Checklist -> What must pass before the result becomes default.
- Deliverable: Evidence Packet -> External and internal citations linked to the claim.

## Runtime Notes

- Mode: baseline
- Live agent success: False
- Model: -
- Calls used: 0

## Demo Snapshot

- Scenario: research_ops_platform
- Selected agent: AnalysisAgent
- Skills: research_brief, validation_planner, build_timeline
- Internal frontier estimate: 0.729
- Bottleneck axis: orchestration_quality
- Release decision: go (all_quality_gates_passed)
- Robust expected utility: 0.748
- Robust worst case: 0.398
- Avg uncertainty: 0.210
- Interop frameworks: 2
- Exported skill entries: 52

## Why This Is Different

- Concentrated value axis: ecosystem_leverage=1.00, interoperability=1.00, product_readiness=0.93.
- Internal frontier estimate=0.729 with bottleneck `orchestration_quality`.
- Ahead of built-in deep-research archetype by +0.205 internal frontier.
- Method edge: routing balances deliverable fit, evidence need, and execution risk instead of forcing one fixed workflow.
- Same command emits a primary deliverable, inspectable runtime artifacts, and an OpenAI/Anthropic skill bundle.

## Artifact Bundle

- Deliverable: docs\demo\research\deliverable.md
- JSON payload: docs\demo\research\showcase.json
- HTML showcase: docs\demo\research\showcase.html
- Press brief: docs\demo\research\press-brief.md
- Bundle manifest: 
- Interop bundle index: -

## Appendix

- Agent comparison winner: AnalysisAgent
- Agent score gap: 0.0017
- Built-in positioning: Ahead of built-in deep-research archetype by +0.205 internal frontier.
- Fact: tool_success_rate=1.0 (measured_run_execution)
- Fact: completion_score=1.0 (measured_run_completion)
- Fact: evidence_records=12 (counted_evidence_bundle)
- Fact: evidence_citations=6 (counted_citations)
- Fact: live_agent_success=False (measured_api_run)
- Heuristic: value_index=84.72 (internal_weighted_heuristic)
- Heuristic: frontier_score=0.7286 (internal_bottleneck_aware_heuristic)
- Heuristic: archetype_gap=0.2047 (built_in_archetype_comparison)
_Generated at 2026-04-05T19:34:41.033426+00:00_
