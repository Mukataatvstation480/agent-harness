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

## Evidence References

- https://github.com/sierra-research/tau-bench
- https://modelcontextprotocol.io/specification/2025-06-18/architecture/index
- https://github.com/SWE-bench/SWE-bench
- internal://research/experiment-promotion-criteria
- https://huggingface.co/gaia-benchmark
- internal://cross/evidence-packet-template

## Openable Files

- Primary Deliverable: docs/demo/research/deliverable.md
- Showcase HTML: docs/demo/research/showcase.html
- Showcase JSON: docs/demo/research/showcase.json
- Press Brief: docs/demo/research/press-brief.md
- Interop Bundle: docs/demo/research/interop_bundle.json
