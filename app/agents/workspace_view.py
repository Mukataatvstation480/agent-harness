"""Streaming workspace/artifact view builders for thread runtime UI consumers."""

from __future__ import annotations

import html
from typing import Any


class ThreadWorkspaceStreamBuilder:
    """Build front-end friendly workspace stream payloads and HTML snapshots."""

    SCHEMA = "agent-harness-workspace-stream/v1"

    def build(self, thread_payload: dict[str, Any]) -> dict[str, Any]:
        executions = thread_payload.get("executions", []) if isinstance(thread_payload.get("executions", []), list) else []
        artifacts = thread_payload.get("artifacts", []) if isinstance(thread_payload.get("artifacts", []), list) else []
        messages = thread_payload.get("messages", []) if isinstance(thread_payload.get("messages", []), list) else []
        events = thread_payload.get("events", []) if isinstance(thread_payload.get("events", []), list) else []
        return {
            "schema": self.SCHEMA,
            "thread_id": thread_payload.get("thread_id", ""),
            "header": {
                "title": thread_payload.get("title", ""),
                "status": thread_payload.get("status", ""),
                "agent_name": thread_payload.get("agent_name", ""),
                "latest_query": thread_payload.get("latest_query", ""),
            },
            "workspace": thread_payload.get("workspace", {}),
            "metrics": {
                "message_count": len(messages),
                "artifact_count": len(artifacts),
                "execution_count": len(executions),
                "event_count": len(events),
            },
            "messages": messages[-8:],
            "artifacts": artifacts[-12:],
            "executions": [
                {
                    "execution_id": item.get("execution_id", ""),
                    "label": item.get("label", ""),
                    "status": item.get("status", ""),
                    "completed_nodes": item.get("graph", {}).get("summary", {}).get("completed_nodes", 0),
                    "node_count": item.get("graph", {}).get("summary", {}).get("node_count", 0),
                    "runnable_nodes": item.get("graph", {}).get("summary", {}).get("runnable_nodes", []),
                }
                for item in executions[-8:]
            ],
            "stream_events": events[-20:],
        }

    def to_html(self, payload: dict[str, Any]) -> str:
        header = payload.get("header", {}) if isinstance(payload.get("header", {}), dict) else {}
        metrics = payload.get("metrics", {}) if isinstance(payload.get("metrics", {}), dict) else {}
        messages = payload.get("messages", []) if isinstance(payload.get("messages", []), list) else []
        artifacts = payload.get("artifacts", []) if isinstance(payload.get("artifacts", []), list) else []
        executions = payload.get("executions", []) if isinstance(payload.get("executions", []), list) else []
        events = payload.get("stream_events", []) if isinstance(payload.get("stream_events", []), list) else []
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Agent Workspace Stream</title>
  <style>
    :root {{
      --bg: #f4efe7;
      --ink: #14213d;
      --accent: #ef476f;
      --accent-2: #118ab2;
      --card: #fffaf3;
      --line: rgba(20,33,61,0.12);
    }}
    body {{ margin:0; font-family: 'Segoe UI', sans-serif; background: radial-gradient(circle at top, #fff7ea, var(--bg)); color:var(--ink); }}
    .page {{ max-width: 1200px; margin: 0 auto; padding: 32px; }}
    .hero {{ padding: 28px; border-radius: 24px; background: linear-gradient(135deg, rgba(239,71,111,0.16), rgba(17,138,178,0.12)); border: 1px solid var(--line); }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-top: 20px; }}
    .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 18px; box-shadow: 0 14px 40px rgba(20,33,61,0.06); }}
    .kicker {{ text-transform: uppercase; letter-spacing: 0.08em; font-size: 12px; color: var(--accent-2); }}
    .value {{ font-size: 32px; font-weight: 700; margin-top: 8px; }}
    ul {{ padding-left: 18px; }}
    li {{ margin: 6px 0; }}
    code {{ background: rgba(20,33,61,0.06); padding: 2px 6px; border-radius: 8px; }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div class="kicker">Workspace Stream</div>
      <h1>{html.escape(str(header.get("title", "")))}</h1>
      <p>Status: <strong>{html.escape(str(header.get("status", "")))}</strong> | Agent: <strong>{html.escape(str(header.get("agent_name", "")))}</strong></p>
      <p>Latest query: {html.escape(str(header.get("latest_query", "")))}</p>
    </section>
    <section class="grid">
      <div class="card"><div class="kicker">Messages</div><div class="value">{int(metrics.get("message_count", 0))}</div></div>
      <div class="card"><div class="kicker">Artifacts</div><div class="value">{int(metrics.get("artifact_count", 0))}</div></div>
      <div class="card"><div class="kicker">Executions</div><div class="value">{int(metrics.get("execution_count", 0))}</div></div>
      <div class="card"><div class="kicker">Events</div><div class="value">{int(metrics.get("event_count", 0))}</div></div>
    </section>
    <section class="grid">
      <div class="card">
        <div class="kicker">Executions</div>
        <ul>{"".join(f"<li><code>{html.escape(str(item.get('label','')))}</code> {html.escape(str(item.get('status','')))} {int(item.get('completed_nodes',0))}/{int(item.get('node_count',0))}</li>" for item in executions) or "<li>No executions.</li>"}</ul>
      </div>
      <div class="card">
        <div class="kicker">Artifacts</div>
        <ul>{"".join(f"<li><code>{html.escape(str(item.get('name','')))}</code> {html.escape(str(item.get('kind','')))}</li>" for item in artifacts) or "<li>No artifacts.</li>"}</ul>
      </div>
      <div class="card">
        <div class="kicker">Messages</div>
        <ul>{"".join(f"<li><strong>{html.escape(str(item.get('role','')))}</strong>: {html.escape(str(item.get('content',''))[:120])}</li>" for item in messages) or "<li>No messages.</li>"}</ul>
      </div>
      <div class="card">
        <div class="kicker">Event Stream</div>
        <ul>{"".join(f"<li><code>{html.escape(str(item.get('event','')))}</code> {html.escape(str(item.get('timestamp','')))}</li>" for item in events) or "<li>No events.</li>"}</ul>
      </div>
    </section>
  </div>
</body>
</html>
"""
