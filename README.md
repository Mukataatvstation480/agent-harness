<p align="right">
  <a href="./README.md"><img alt="English" src="https://img.shields.io/badge/Language-English-0f766e?style=for-the-badge"></a>
  <a href="./README.zh-CN.md"><img alt="简体中文" src="https://img.shields.io/badge/%E8%AF%AD%E8%A8%80-%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-2563eb?style=for-the-badge"></a>
</p>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:081826,35:0F766E,70:2563EB,100:F59E0B&height=220&section=header&text=Agent%20Harness&fontSize=54&fontColor=ffffff&desc=Turn%20one%20request%20into%20an%20auditable%20agent%20product.&descAlignY=68&animation=fadeIn" alt="Agent Harness banner"/>
</p>

<p align="center">
  <b>Agent Harness turns one request into a mission pack: deliverable, execution plan, evidence packet, benchmark posture, and ecosystem-portable bundle.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Routing-robust_frontier-0f766e?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Execution-Harness%20Engine-2563eb?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Eval-harness--lab-f59e0b?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Interop-OpenAI%20%7C%20Anthropic-111827?style=for-the-badge"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/LangGraph-Orchestrated-0B1020"/>
  <img src="https://img.shields.io/badge/CLI-Typer-111827"/>
  <img src="https://img.shields.io/badge/Tests-87%20passed-16a34a"/>
</p>

---

## Framework Diagram

![Agent Harness Framework Diagram](docs/d5_260402_5995__QakBh2Z.jpg)

Agent Harness is built around one thesis:

`User Request -> Agent Router -> Agent Council -> Skill Router -> Harness Engine -> Mission Pack -> Evidence / Lab / Showcase / Interop`

This repo is not just a router and not just a skill list. It is a system that:

1. chooses better
2. executes with evidence
3. benchmarks against the right benchmark family before release
4. packages outputs as reusable mission artifacts
5. exports capabilities into external ecosystems

---

## Why This Exists

Most projects in this space are strong in only one direction:

- flow-first systems are good at orchestration, weak at proof
- research-first systems are deep, weak at packaging
- skill hubs are broad, weak at governance and release gating

Agent Harness is designed to unify all three with one output contract.

It turns one request into:

- a routing decision
- an execution plan
- an evidence packet
- a mission-specific deliverable set
- a benchmark-fit statement with honest gaps
- a launch-ready showcase
- an interop export for outside ecosystems

The important difference is that the front-end object is no longer "a proposal page".
It is a `mission pack`, which can represent:

- strategy rollout
- research promotion packet
- operations playbook
- implementation spec

That keeps the framework general instead of drifting into a one-demo toy.

---

## Launch Demo

### Demo Gallery

Published demo snapshots live under `docs/demo/`. Runtime-generated `reports/` outputs stay local and are intentionally gitignored.

Browse all tracked snapshots: [docs/demo/README.md](./docs/demo/README.md)

<table>
  <tr>
    <td width="33%" valign="top">
      <h3>Live Fintech Launch</h3>
      <p><img src="./docs/demo/live/showcase.png" alt="Live showcase screenshot"></p>
      <p>Real API-backed regulated copilot launch pack with mission summary, evidence packet, benchmark fit, and release recommendation.</p>
      <p><a href="./docs/demo/live/showcase.html">Open HTML Snapshot</a></p>
      <p><a href="./docs/demo/live/press-brief.md">Open Press Brief</a></p>
    </td>
    <td width="33%" valign="top">
      <h3>Enterprise Rollout Pack</h3>
      <p><img src="./docs/demo/enterprise/showcase.png" alt="Enterprise rollout screenshot"></p>
      <p>Enterprise operating-layer rollout for internal workflows, showing deployment posture, governance gates, and portable capability export.</p>
      <p><a href="./docs/demo/enterprise/showcase.html">Open HTML Snapshot</a></p>
      <p><a href="./docs/demo/enterprise/press-brief.md">Open Press Brief</a></p>
    </td>
    <td width="33%" valign="top">
      <h3>Research Promotion Pack</h3>
      <p><img src="./docs/demo/research/showcase.png" alt="Research mission screenshot"></p>
      <p>Applied research promotion artifact with benchmark readout, evidence-backed release packet, and promotion checklist.</p>
      <p><a href="./docs/demo/research/showcase.html">Open HTML Snapshot</a></p>
      <p><a href="./docs/demo/research/press-brief.md">Open Press Brief</a></p>
    </td>
  </tr>
</table>

### What The Demo Shows

The current showcase UI is intentionally front-loaded with:

1. mission summary
2. deliverable package
3. phased rollout and execution tracks
4. evidence bundle and external citations
5. benchmark fit and honest capability boundary
6. framework comparison, agent comparison, and appendix

The live fintech snapshot is generated with real model calls. The enterprise and research snapshots are deterministic, so they can be shipped in-repo and stay reproducible.

---

## Feature Highlights

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>What Typical Repos Stop At</h3>
      <ul>
        <li>single-agent selection</li>
        <li>top-k or relevance-only skill choice</li>
        <li>answer generation without formal evidence</li>
        <li>ad hoc evaluation</li>
        <li>one-off demos tied to a single output type</li>
        <li>closed internal ecosystem</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>What Agent Harness Adds</h3>
      <ul>
        <li>agent council and collaboration-aware routing</li>
        <li><code>robust_frontier</code> skill selection under uncertainty</li>
        <li>mission-pack output contract across strategy, research, ops, and implementation tasks</li>
        <li>trace, response contract, and routing analysis</li>
        <li><code>harness-lab</code> leaderboard and release gate</li>
        <li>studio showcase and OpenAI / Anthropic interop export</li>
      </ul>
    </td>
  </tr>
</table>

### Capability Matrix

| Capability | Typical Repo | Agent Harness |
|---|---|---|
| Agent routing | single winner | primary agent + agent council |
| Skill routing | relevance/top-k | `robust_frontier` over reliability, uncertainty, downside |
| Execution | tool loop | harness engine with tools, memory, guardrails, live API |
| Evidence | partial logs | trace + response contract + routing analysis |
| Evaluation | ad hoc | `harness-lab` with leaderboard + release gate |
| Product output | answer only | mission pack + HTML + JSON + press brief + manifest |
| Ecosystem | closed | OpenAI / Anthropic skill interop |

---

## Architecture

### Routing Layer

- `Agent Router`: scores candidate agents against intent, complexity, and risk
- `Agent Council`: expands available capabilities when collaboration is useful
- `Skill Router`: chooses the final skill portfolio using `robust_frontier`

### Skill Layer

A `skill` is the atomic capability unit of the framework. It carries:

- metadata
- strengths / weaknesses
- cost
- reliability
- uncertainty signals
- category / tier / synergies / conflicts

Skills can come from:

- built-in local registry
- marketplace-style ecosystem sources
- runtime external skill loading
- OpenAI / Anthropic compatible exported bundles

### Harness Layer

`harness` is the execution operating system around routing. It is responsible for:

- tool discovery
- recipe selection
- memory reuse
- guardrails
- live API enhancement
- evaluation
- value scoring
- visual payload generation
- report generation
- research lab benchmarking

This is why the repo is not just a router.

### Studio Layer

`studio-showcase` turns runtime evidence into a mission-pack product:

- strategy / research / ops / implementation views
- benchmark comparison and fit statement
- agent comparison
- generated result excerpt
- appendix for internal skills and tools

### Interop Layer

The framework can export skills for outside ecosystems so the project is not locked inside its own runtime.

---

## Core Method

### Risk-Calibrated Frontier Routing

The skill selector does not optimize only relevance. It jointly considers:

- relevance
- diversity
- redundancy penalty
- synergy
- empirical reliability
- uncertainty penalty
- downside risk

The main exposed objectives are:

- `robust_expected_utility`
- `robust_worst_case_utility`
- `avg_uncertainty`

### Research-Grade Release Gating

`harness-lab` runs repeatable scenario suites and returns:

- leaderboard
- pass rate
- value index
- security alignment
- release decision: `go / caution / block`

---

## Benchmark Posture

Agent Harness is benchmark-aware, not benchmark-maxed-out yet.

Benchmark families this framework is built to map against:

- `GAIA`: evidence-backed multi-step reasoning and retrieval-heavy tasks
- `TAU-bench` and `TheAgentCompany`: enterprise workflow execution and knowledge-work packaging
- `WebArena`: browser-actuated long-horizon workflows
- `SWE-bench Verified`: code issue resolution with implementation proof

Current strength:

- turning reasoning into auditable mission artifacts
- combining evidence, governance, and release gating in one pipeline
- packaging the same capability set for external ecosystems

Current honest gap:

- no claim of state-of-the-art on browser benchmarks yet
- no claim of state-of-the-art on code-fix benchmarks yet
- real enterprise connectors still need to grow beyond skeleton providers

---

## Quick Start

### 1. Install

```bash
pip install -r requirements.txt
```

### 2. Run the core router

```bash
python -m app.main run "Compare two rollout plans and highlight governance risk" --mode deep --contract
```

### 3. Run the harness engine

```bash
python -m app.main harness "Prepare a governance-ready execution memo" --mode balanced
```

### 4. Generate a showcase

```bash
python -m app.main studio-showcase "Design a flagship AI operating plan" --mode deep --lab-preset broad --tag flagship
```

### 5. Inspect generalized mission profiles

```bash
python -m app.main mission-profiles
python -m app.main proposal-scenarios
python -m app.main harness-mission "Design an implementation roadmap with migration risks and validation gates."
```

### 6. Generate a launch demo

```bash
python -m app.main launch-demo --output-dir reports/launch_demo --tag press
```

### 7. Generate a live API launch demo

Set environment variables first:

```bash
set AGENT_HARNESS_MODEL_BASE_URL=https://your-endpoint/v1
set AGENT_HARNESS_MODEL_API_KEY=your_api_key
set AGENT_HARNESS_MODEL_NAME=your_model
```

Then run:

```bash
python -m app.main launch-demo --output-dir reports/live_launch_demo --tag live --live-agent --max-model-calls 6
```

### 8. Run research lab

```bash
python -m app.main harness-lab --preset broad --repeats 2 --output reports/lab.json
python -m app.main harness-lab-product --preset broad --repeats 2 --tag release --output-dir reports
```

### 9. Export interop bundles

```bash
python -m app.main skills-interop-export --framework all --output-dir reports/skills_interop
```

### 10. Run tests

```bash
pytest -q
```

---

## Command Map

| Goal | Command |
|---|---|
| basic routing | `python -m app.main run "<query>"` |
| trace and reasoning | `python -m app.main trace "<query>" --views` |
| harness execution | `python -m app.main harness "<query>"` |
| mission pack | `python -m app.main harness-mission "<query>"` |
| value card | `python -m app.main harness-value "<query>"` |
| visual payload | `python -m app.main harness-visual "<query>" --output reports/visual.json` |
| mission profiles | `python -m app.main mission-profiles` |
| showcase | `python -m app.main studio-showcase "<query>" --tag demo` |
| launch demo | `python -m app.main launch-demo --tag press` |
| research lab | `python -m app.main harness-lab --preset broad` |
| interop export | `python -m app.main skills-interop-export --framework all` |

---

## Repository Map

### Core runtime

- `app/routing/` - agent routing, skill routing, complementarity, robust frontier
- `app/policy/` - system modes, governance, robustness policy
- `app/personality/` - profiles and adaptation
- `app/coordination/` - conflict, dissent, consensus
- `app/core/` - state, contracts, shared protocol

### Execution and productization

- `app/harness/` - execution engine, manifests, tools, reports, lab, value, visuals
- `app/studio/` - flagship showcase builder and launch packaging
- `app/tracing/` - trace rendering and quality analysis
- `app/utils/` - console and display helpers

### Skills and ecosystem

- `app/skills/` - built-in and external skill registry
- `app/ecosystem/` - marketplace signals, providers, imports
- `app/skills/interop.py` - OpenAI / Anthropic compatibility export

### Assets and artifacts

- `docs/` - architecture prompts and images
- `reports/` - generated demos, lab bundles, showcases
- `tests/` - regression coverage

---

## Current Status

- `robust_frontier` routing is implemented
- agent council routing is implemented
- harness engine and research lab are implemented
- mission-pack output contract is implemented
- studio showcase and launch demo are implemented
- OpenAI / Anthropic interop export is implemented
- current local test result: `87 passed`

---

## Recommended First Experience

```bash
python -m app.main launch-demo --output-dir reports/launch_demo --tag press
python -m app.main studio-showcase "Design a flagship AI operating plan" --mode deep --lab-preset broad --tag studio
```

Then open:

- `docs/demo/live/showcase.html`
- `docs/demo/enterprise/showcase.html`
- `docs/demo/research/showcase.html`

These communicate the project better than a plain CLI trace.
