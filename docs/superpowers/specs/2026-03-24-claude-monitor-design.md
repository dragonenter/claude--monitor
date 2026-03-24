# Claude Code Monitor — Design Spec

## Overview

A real-time monitoring dashboard for Claude Code that visualizes agent execution flow, tool calls, and efficiency metrics. Built on Claude Code's official hooks mechanism.

## Problem

When Claude Code works on complex tasks, it dispatches subagents that may:
- Repeat work the main agent already did (duplicate file reads, searches)
- Miss critical context from the main agent's decisions
- Waste tokens and time on approaches that get discarded

Users have no visibility into this process.

## Architecture

```
Claude Code (hooks: HTTP POST)
    ├── SessionStart / SessionEnd
    ├── SubagentStart / SubagentStop
    ├── PreToolUse / PostToolUse
    │
    ▼
Monitor Server (Python aiohttp, single process)
    ├── POST /events — receive hook events
    ├── GET /api/sessions — list sessions
    ├── GET /api/session/:id — session data
    ├── GET /stream — SSE push to frontend
    ├── GET / — serve dashboard HTML
    │
    ├── In-memory store (dict by session_id)
    ├── Agent tree builder (agent_id → parent via timing)
    ├── Duplicate detector (same grep pattern / file read across agents)
    └── Metrics calculator (call counts, durations, efficiency)

    ▼
Dashboard (single HTML, vanilla JS + EventSource)
    ├── Top: session selector (multi-session support)
    ├── Left: agent tree (real-time status)
    ├── Center: event feed (live, with duplicate/anomaly badges)
    ├── Right: metrics panel (call counts, efficiency, alerts)
    ├── Drill-down: click agent → call trace (方案1)
    └── Drill-down: click context → prompt audit (方案2)
```

## Data Model

### Event (from hooks)

All events share common fields from Claude Code hooks:
```json
{
  "session_id": "abc123",
  "cwd": "/project/path",
  "hook_event_name": "PreToolUse"
}
```

Server adds: `received_at` timestamp.

### Session

```python
{
  "session_id": str,
  "cwd": str,
  "started_at": float,
  "status": "active" | "ended",
  "agents": {agent_id: AgentNode},
  "events": [Event],
  "metrics": Metrics
}
```

### AgentNode

```python
{
  "agent_id": str,          # "main" or from SubagentStart
  "agent_type": str,        # "Explore", "Plan", "general", etc.
  "parent_id": str | None,  # inferred from timing
  "status": "running" | "done" | "failed",
  "tool_calls": [ToolCall],
  "started_at": float,
  "ended_at": float | None
}
```

### ToolCall

```python
{
  "tool_use_id": str,
  "tool_name": str,
  "tool_input": dict,
  "agent_id": str,
  "started_at": float,
  "ended_at": float | None,
  "is_duplicate": bool,
  "duplicate_of": str | None  # agent_id that did it first
}
```

## Multi-Session Support

| Scenario | Handling |
|----------|----------|
| Multiple folders, multiple Claudes | Different session_id + cwd, separate entries |
| `claude -r` resume | New session_id, same cwd, grouped under project |
| Same folder, new Claude | New session_id, independent entry |

Dashboard groups by `cwd`, shows sessions as a list within each project.

## Duplicate Detection

Compare across agents within the same session:
- **Grep**: normalize pattern, check if same pattern searched by different agent
- **Read**: check if same file_path read by different agent
- **Glob**: check if same glob pattern used by different agent

Mark as `is_duplicate: true` with reference to which agent did it first.

## Parent-Agent Inference

`parent_agent_id` is not provided by hooks. Inference strategy:
1. When main agent calls Agent tool (seen in PreToolUse with tool_name="Agent")
2. Shortly after, SubagentStart fires with new agent_id
3. Correlate by timing window (<1s) to establish parent-child relationship

## Deliverables

1. `server.py` — monitoring server (aiohttp)
2. `dashboard.html` — single-file frontend
3. `install.py` — auto-configure Claude Code hooks in settings.json

## Tech Stack

- Python 3.8+ (aiohttp, no other deps)
- Vanilla HTML/CSS/JS (no build step, no framework)
- SSE for real-time push

## Port

Default: 1010 (configurable via CLI arg)
