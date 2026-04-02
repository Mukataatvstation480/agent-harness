# Agent Harness Visual Schema

This file is intentionally written as a direct image-generation prompt schema.

---BEGIN PROMPT---

[Style & Meta-Instructions]
High-fidelity scientific schematic, technical vector illustration, clean white background, distinct boundaries, academic textbook style. High resolution 4k, strictly 2D flat design with subtle isometric elements. Use crisp black-grey outlines, precise arrow geometry, evenly spaced panels, controlled typography, and restrained professional color fills. Every module must look like a physical diagram object, not an abstract word cloud. No decorative characters, no photorealism, no noisy gradients, no watermark.

[LAYOUT CONFIGURATION]
* **Selected Layout**: Hybrid Layout combining Linear Pipeline and Central Hub
* **Composition Logic**: A left-to-right decision pipeline feeds into one large central engine, and that central engine radiates to four structured output panels on the right and lower-right. The visual message is: one user request enters, multi-stage routing happens, a central harness executes and evaluates, and the system emits auditable product artifacts rather than only text.
* **Color Palette**: Professional Pastel and scientific UI palette: Azure Blue, Slate Grey, Mint Green, Coral Orange, soft Amber, light Cyan.

[ZONE 1: FAR LEFT - USER REQUEST INTAKE]
* **Container**: Tall rounded rectangle panel on the far left edge
* **Visual Structure**: A stacked set of three document sheets with the top sheet slightly tilted forward, a small speech bubble icon above the sheets, and a narrow horizontal input bar beneath them. Beneath the document stack, place three tiny bullet lines to imply task intent, governance need, and research need.
* **Key Text Labels**: "User Request", "Task Prompt", "Growth + Governance + Research"

[ZONE 2: LEFT-CENTER - AGENT DECISION LAYER]
* **Container**: Medium rectangular panel immediately to the right of Zone 1
* **Visual Structure**: Two vertically stacked routing blocks. The top block is a rectangular router board containing four small agent tiles arranged in a 2x2 grid. One tile is highlighted with a darker outline to indicate the selected agent. The lower block is a smaller council strip showing three miniature head-and-shoulder icons connected by thin lines to indicate agent collaboration. Between the upper and lower blocks, place a tiny selector diamond to imply ranking and tie-breaking.
* **Key Text Labels**: "Agent Router", "Agent Council", "Primary Agent", "Runner-up Agent"

[ZONE 3: MID-LEFT - SKILL ROUTING LAYER]
* **Container**: Wide rectangular decision panel between Zone 2 and Zone 4
* **Visual Structure**: A horizontal skill portfolio board with six small rounded tiles inside it. Three tiles are bright and selected, three are muted and rejected. Above the selected tiles, place a thin frontier curve line with three circular checkpoints to indicate robust frontier selection. Beneath the tiles, place three tiny meter bars representing reliability, uncertainty, and downside risk.
* **Key Text Labels**: "Skill Router", "robust_frontier", "Selected Skills", "Reliability", "Uncertainty", "Downside Risk"

[ZONE 4: CENTER - HARNESS EXECUTION HUB]
* **Container**: Large central rounded square, visually dominant, thicker boundary than all other zones
* **Visual Structure**: A central engine block containing one large gear icon in the middle. Around the gear, arrange four internal submodules in a ring:
  - top: a memory chip icon
  - right: a shield icon
  - bottom: a toolbox icon
  - left: a small API plug icon
  Connect the four submodules to the central gear with straight spokes. Add a thin circular ring around the gear and submodules to suggest orchestration. In the lower part of the hub, place a small execution timeline with four rectangular steps connected in sequence.
* **Key Text Labels**: "Harness Engine", "Memory", "Guardrails", "Tools", "Live API / Local Skills", "Execution Loop"

[ZONE 5: UPPER RIGHT - EVIDENCE LAYER]
* **Container**: Top-right rectangular panel
* **Visual Structure**: Three vertically stacked evidence cards. The first card contains a branching trace tree icon. The second card contains a checklist card icon with three tick marks. The third card contains a tiny analytics board with line chart and bar chart. Align the three cards evenly with clear borders.
* **Key Text Labels**: "Trace", "Response Contract", "Routing Analysis", "Evidence Layer"

[ZONE 6: RIGHT-CENTER - RESEARCH LAB LAYER]
* **Container**: Rectangular panel directly below Zone 5
* **Visual Structure**: A leaderboard table with five rows and four columns, topped by a small laboratory flask icon on the left and a gated checkpoint icon on the right. Highlight one champion row with a colored stripe. At the right side of the table, place a traffic-light style decision indicator with green, yellow, red dots, and green emphasized.
* **Key Text Labels**: "Harness Lab", "Leaderboard", "Release Gate", "GO / CAUTION / BLOCK"

[ZONE 7: LOWER RIGHT - PRODUCT SHOWCASE LAYER]
* **Container**: Large lower-right rectangular showcase panel
* **Visual Structure**: A mini dashboard layout containing:
  - one large hero card at the top
  - two smaller cards beneath it
  - one tiny HTML page thumbnail
  - one JSON bracket icon
  - one press brief page icon
  Arrange these elements like a polished product board, not like a raw table.
* **Key Text Labels**: "Studio Showcase", "Value Card", "Visual Payload", "Launch Demo", "HTML", "JSON", "Press Brief"

[ZONE 8: FAR RIGHT EDGE - ECOSYSTEM INTEROP LAYER]
* **Container**: Narrow vertical panel on the far right
* **Visual Structure**: Two export package boxes stacked vertically, each box containing a small manifest sheet and an outward arrow. Add a tiny connector rail between the boxes and the product showcase panel to indicate exportability into outside ecosystems.
* **Key Text Labels**: "OpenAI Interop", "Anthropic Interop", "Portable Skills", "External Ecosystem"

[CONNECTIONS]
1. A thick solid horizontal arrow from Zone 1 to Zone 2 labeled "Intent Intake"
2. A thick solid horizontal arrow from Zone 2 to Zone 3 labeled "Agent-to-Skill Routing"
3. A thick solid horizontal arrow from Zone 3 to Zone 4 labeled "Execution Portfolio"
4. A wide branching arrow from Zone 4 upward-right into Zone 5 labeled "Trace + Contract"
5. A wide branching arrow from Zone 4 rightward into Zone 6 labeled "Benchmark + Release Gate"
6. A wide branching arrow from Zone 4 downward-right into Zone 7 labeled "Launch-ready Product Output"
7. A medium solid arrow from Zone 7 to Zone 8 labeled "Interop Export"
8. A curved dotted arrow looping back from Zone 6 to Zone 3 labeled "Lab Feedback"
9. A curved dotted arrow looping back from Zone 5 to Zone 2 labeled "Audit Feedback"

[INPUT DATA]
Agent Harness is an agent operating system. A user request first enters an agent router, which compares multiple candidate agents and may form an agent council. The selected agent context is passed into a skill router, which uses robust_frontier routing to choose a skill portfolio under reliability, uncertainty, and downside-risk constraints. The chosen skills are executed by a central Harness Engine that coordinates tools, memory, guardrails, and live API or local skill execution. The engine produces trace, response contract, and routing analysis for evidence. It also runs a research evaluation layer called Harness Lab, which generates a leaderboard and a release decision such as go, caution, or block. On the product side, the system emits a value card, visual payload, studio showcase, and launch demo outputs such as HTML, JSON, and press brief artifacts. Finally, the framework exports capabilities into external ecosystems through OpenAI and Anthropic interop bundles. The full conceptual message is: turn one request into an auditable, benchmarked, launch-ready, ecosystem-portable agent product.

---END PROMPT---

