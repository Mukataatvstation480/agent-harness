<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0B1020,35:0EA5E9,70:22C55E,100:F59E0B&height=230&section=header&text=Agent%20Harness&fontSize=56&fontColor=ffffff&desc=Agents%20think.%20Skills%20act.%20The%20harness%20decides.&descAlignY=68&animation=fadeIn" alt="Agent Harness banner"/>
</p>

<p align="center">
  <b>A multi-agent system where each agent dynamically selects complementary skills with full routing trace.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Harness-Engineering-0ea5e9?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Visual-Demo%20Ready-22c55e?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Security-Allow%20%7C%20Challenge%20%7C%20Block-f59e0b?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Showcase-Impact%20Lens-9333ea?style=for-the-badge"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/LangGraph-Orchestrated-121D33"/>
  <img src="https://img.shields.io/badge/CLI-Typer-black"/>
  <img src="https://img.shields.io/badge/Output-JSON%20Protocol-brightgreen"/>
</p>

## Why This Repo Turns Heads

Most agent repos stop at "it runs."  
This one ships the data model that powers high-impact visuals from day one:

- Value scoring: `reliability + observability + adaptability + safety + innovation`
- Front-end protocol: radar, timeline, discovery board, security lane, network graph, hero cards
- First-screen blueprint: panel layout + refs + motion hints
- Event stream: replay-ready timeline for animated storytelling
- Scenario packs: one-click multi-run comparison to prove business value
- Auto optimizer: find best `mode + recipe` config per query

## First Screen Architecture

```mermaid
flowchart LR
    A[User Query] --> B[Security Preflight]
    B --> C[Agent + Skill Routing]
    C --> D[Tool Discovery + Recipe Loop]
    D --> E[Guardrails + Tool Execution]
    E --> F[Value Card]
    F --> G[Visual Payload]
    G --> H[First Screen Blueprint]
    G --> I[Event Stream Playback]
    G --> J[Showcase Comparison]
```

## Visual Demo Power Map

| You Need to Show | Already Exported | Data Source |
|---|---|---|
| KPI hero strip | `kpis` + `value_index` | `harness-value` / `harness-visual` |
| Radar chart | `radar.labels` + `radar.values` | `harness-visual` |
| Gantt timeline | `timeline[]` with step status | `harness-visual` |
| Discovery scatter | `discovery_board[]` (score/novelty/risk) | `harness-visual` |
| Security lane | `security_board` (preflight + step actions) | `harness-visual` |
| Force graph | `tool_network.nodes/links` | `harness-visual` |
| Animated replay | `event_stream[]` with timestamps | `harness-stream` |
| Multi-scenario leaderboard | `comparison.rows` + `best` | `harness-showcase` |
| Best strategy recommendation | `best + recommendation` | `harness-optimize` |

## Quick Start

```bash
pip install -r requirements.txt
python -m app.main run "Compare two rollout plans and highlight compliance risk"
```

## One-Liners That Generate "Wow" Data

```bash
# 1) Value card (great for headline KPI section)
python -m app.main harness-value "compare safe rollout strategies" --json

# 2) Full visual payload (single-run dashboard data)
python -m app.main harness-visual "map ecosystem opportunities" --output reports/visual.json

# 3) First-screen blueprint (layout + motion hints)
python -m app.main harness-blueprint "audit governance posture" --output reports/blueprint.json

# 4) Event playback stream (animation timeline)
python -m app.main harness-stream "audit governance posture" --output reports/stream.json

# 5) Multi-scenario showcase (side-by-side comparison)
python -m app.main harness-showcase --pack impact-lens --output reports/showcase.json

# 6) Auto-select best mode + recipe for this query
python -m app.main harness-optimize "design a safe and innovative rollout strategy" --output reports/optimize.json
```

## Real Payload Glimpse

```json
{
  "kpis": {
    "value_index": 86.63,
    "reliability": 0.85,
    "safety": 0.72,
    "innovation": 0.91
  },
  "radar": {
    "labels": ["reliability", "observability", "adaptability", "safety", "innovation"],
    "values": [85.0, 84.0, 88.0, 72.0, 91.0]
  },
  "hero_cards": [
    {"title": "Reliability Signal", "headline": "85% reliable execution"},
    {"title": "Safety Signal", "headline": "72% safety posture"},
    {"title": "Innovation Signal", "headline": "91% innovation density"}
  ]
}
```

## Showcase Packs

| Pack | Storyline | Best For |
|---|---|---|
| `impact-lens` | governance + ecosystem + architecture evolution | investor/demo first screen |
| `security-first` | attack defense + constrained audit flow | enterprise/security buyers |

List packs:

```bash
python -m app.main harness-showcase-packs
```

## Core Harness Files

- `app/harness/manifest.py`
- `app/harness/discovery.py`
- `app/harness/security.py`
- `app/harness/recipes.py`
- `app/harness/value.py`
- `app/harness/visuals.py`
- `app/harness/presentation.py`
- `app/harness/stream.py`
- `app/harness/showcase.py`
- `app/harness/optimizer.py`
- `app/harness/engine.py`

Visual protocol docs:

- `examples/visual_payload_contract.md`
- `examples/harness_recipe.sample.json`

## Suggested GitHub Topics

`ai`, `llm`, `agent`, `multi-agent`, `langchain`, `agent-framework`, `agent-routing`, `skill`, `tools`, `orchestration`, `harness`, `evaluation`

---

If you are building a flashy demo page, this repo already gives you:

1. The numbers (value KPI)
2. The narrative (hero cards + storyline)
3. The motion timeline (event stream)
4. The visual skeleton (first-screen blueprint)
5. The proof (multi-scenario comparison + optimizer recommendation)

