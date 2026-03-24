#!/usr/bin/env python3
"""Claude Code Monitor — Real-time monitoring server for Claude Code agent execution."""

import argparse
import asyncio
import json
import os
import time
from collections import defaultdict
from pathlib import Path

from aiohttp import web

# ---------------------------------------------------------------------------
# Data store (in-memory)
# ---------------------------------------------------------------------------

sessions: dict[str, dict] = {}
sse_queues: list[asyncio.Queue] = []


def get_or_create_session(session_id: str, cwd: str = "") -> dict:
    if session_id not in sessions:
        sessions[session_id] = {
            "session_id": session_id,
            "cwd": cwd,
            "started_at": time.time(),
            "status": "active",
            "agents": {},
            "events": [],
            "tool_calls": {},       # tool_use_id -> ToolCall
            "pending_agent_dispatch": None,  # for parent inference
            "skills": [],           # list of {name, invoked_at}
            "tasks": {},            # task_id -> {subject, status, ...}
        }
    s = sessions[session_id]
    if cwd and not s["cwd"]:
        s["cwd"] = cwd
    return s


def ensure_main_agent(session: dict):
    if "main" not in session["agents"]:
        session["agents"]["main"] = {
            "agent_id": "main",
            "agent_type": "Main",
            "parent_id": None,
            "status": "running",
            "tool_calls": [],
            "started_at": session["started_at"],
            "ended_at": None,
        }


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

def check_duplicate(session: dict, agent_id: str, tool_name: str, tool_input: dict) -> tuple[bool, str | None]:
    """Check if this tool call duplicates one from a different agent."""
    if tool_name == "Grep":
        key = ("Grep", tool_input.get("pattern", ""), tool_input.get("path", ""))
    elif tool_name == "Read":
        key = ("Read", tool_input.get("file_path", ""))
    elif tool_name == "Glob":
        key = ("Glob", tool_input.get("pattern", ""), tool_input.get("path", ""))
    else:
        return False, None

    for tc in session.get("_dedup_log", []):
        if tc["key"] == key and tc["agent_id"] != agent_id:
            return True, tc["agent_id"]

    if "_dedup_log" not in session:
        session["_dedup_log"] = []
    session["_dedup_log"].append({"key": key, "agent_id": agent_id})
    return False, None


# ---------------------------------------------------------------------------
# Context tracking (for context audit — 方案2)
# ---------------------------------------------------------------------------

def track_context(session: dict, agent_id: str, tool_name: str, tool_input: dict):
    """Track what each agent knows (files read, searches done, facts learned)."""
    if "agent_context" not in session:
        session["agent_context"] = {}
    if agent_id not in session["agent_context"]:
        session["agent_context"][agent_id] = {
            "files_read": [],       # file paths
            "searches": [],         # grep/glob patterns
            "agent_prompts": [],    # prompts sent to subagents
        }
    ctx = session["agent_context"][agent_id]

    if tool_name == "Read":
        fp = tool_input.get("file_path", "")
        if fp and fp not in ctx["files_read"]:
            ctx["files_read"].append(fp)
    elif tool_name == "Grep":
        pat = tool_input.get("pattern", "")
        path = tool_input.get("path", "./")
        entry = f'"{pat}" in {path}'
        if entry not in ctx["searches"]:
            ctx["searches"].append(entry)
    elif tool_name == "Glob":
        pat = tool_input.get("pattern", "")
        entry = f'glob "{pat}"'
        if entry not in ctx["searches"]:
            ctx["searches"].append(entry)
    elif tool_name == "Agent":
        prompt = tool_input.get("prompt", "")
        ctx["agent_prompts"].append(prompt[:500])


def compute_context_audit(session: dict, agent_id: str) -> dict:
    """Compare what parent knew vs what was passed to this subagent."""
    agent = session["agents"].get(agent_id)
    if not agent or not agent.get("parent_id"):
        return {"score": 100, "present": [], "missing": []}

    parent_id = agent["parent_id"]
    parent_ctx = session.get("agent_context", {}).get(parent_id, {})
    child_ctx = session.get("agent_context", {}).get(agent_id, {})

    # Find the Agent tool call that dispatched this subagent
    dispatch_prompt = ""
    for e in session["events"]:
        if (e.get("hook_event_name") == "PreToolUse"
                and e.get("tool_name") == "Agent"
                and e.get("agent_id") == parent_id):
            dispatch_prompt = e.get("tool_input", {}).get("prompt", "")

    # What parent knew
    parent_files = set(parent_ctx.get("files_read", []))
    parent_searches = set(parent_ctx.get("searches", []))

    # What child re-did (duplicates = context not passed)
    child_files = set(child_ctx.get("files_read", []))
    child_searches = set(child_ctx.get("searches", []))

    # Files the child re-read that parent already knew
    reread_files = parent_files & child_files
    researched = parent_searches & child_searches

    present = []
    missing = []

    # Check what was mentioned in the prompt vs what parent knew
    for f in parent_files:
        short = f.split("/")[-1] if "/" in f else f
        if short in dispatch_prompt or f in dispatch_prompt:
            present.append({"type": "file", "value": f, "note": "mentioned in prompt"})
        elif f in reread_files:
            missing.append({"type": "file", "value": f, "note": "child re-read this file"})
        else:
            # Not re-read, might not be relevant
            present.append({"type": "file", "value": f, "note": "not needed by child"})

    for s in parent_searches:
        if any(part in dispatch_prompt for part in s.split('"') if part.strip()):
            present.append({"type": "search", "value": s, "note": "mentioned in prompt"})
        elif s in researched:
            missing.append({"type": "search", "value": s, "note": "child re-searched"})

    total = len(present) + len(missing)
    score = round((len(present) / max(total, 1)) * 100)

    return {
        "score": score,
        "present": present,
        "missing": missing,
        "dispatch_prompt": dispatch_prompt[:1000],
        "parent_id": parent_id,
        "parent_files_count": len(parent_files),
        "parent_searches_count": len(parent_searches),
    }


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(session: dict) -> dict:
    total_calls = len(session["events"])
    tool_events = [e for e in session["events"] if e["hook_event_name"] in ("PreToolUse", "PostToolUse")]
    pre_events = [e for e in session["events"] if e["hook_event_name"] == "PreToolUse"]
    duplicates = sum(1 for e in pre_events if e.get("_is_duplicate"))
    agents_total = len(session["agents"])
    agents_active = sum(1 for a in session["agents"].values() if a["status"] == "running")

    files_read = set()
    for e in pre_events:
        if e.get("tool_name") == "Read":
            fp = e.get("tool_input", {}).get("file_path", "")
            if fp:
                files_read.add(fp)

    return {
        "total_events": total_calls,
        "tool_calls": len(pre_events),
        "duplicates": duplicates,
        "efficiency": round((1 - duplicates / max(len(pre_events), 1)) * 100, 1),
        "agents_total": agents_total,
        "agents_active": agents_active,
        "files_read": len(files_read),
        "duration": time.time() - session["started_at"],
    }


def _tool_short_summary(tool_name: str, tool_input: dict) -> str:
    """Short summary of a tool call for task operation log."""
    if tool_name == "Grep":
        return f'搜索 "{tool_input.get("pattern", "")[:40]}"'
    elif tool_name == "Read":
        fp = tool_input.get("file_path", "")
        return f'读取 {fp.split("/")[-1] if "/" in fp else fp}'
    elif tool_name == "Edit":
        fp = tool_input.get("file_path", "")
        return f'编辑 {fp.split("/")[-1] if "/" in fp else fp}'
    elif tool_name == "Write":
        fp = tool_input.get("file_path", "")
        return f'写入 {fp.split("/")[-1] if "/" in fp else fp}'
    elif tool_name == "Bash":
        return f'$ {tool_input.get("command", "")[:50]}'
    elif tool_name == "Agent":
        return f'派发 Agent: {tool_input.get("prompt", "")[:40]}'
    elif tool_name == "Glob":
        return f'搜索文件 "{tool_input.get("pattern", "")[:30]}"'
    return tool_name


# ---------------------------------------------------------------------------
# Event processing
# ---------------------------------------------------------------------------

def process_event(data: dict) -> dict:
    session_id = data.get("session_id", "unknown")
    cwd = data.get("cwd", "")
    event_name = data.get("hook_event_name", "")
    now = time.time()

    session = get_or_create_session(session_id, cwd)
    ensure_main_agent(session)

    event = {
        **data,
        "received_at": now,
    }

    agent_id = data.get("agent_id") or "main"

    if event_name == "SessionStart":
        session["started_at"] = now
        session["status"] = "active"

    elif event_name == "SessionEnd":
        session["status"] = "ended"
        for a in session["agents"].values():
            if a["status"] == "running":
                a["status"] = "done"
                a["ended_at"] = now

    elif event_name == "SubagentStart":
        sub_id = data.get("agent_id", f"agent-{now}")
        sub_type = data.get("agent_type", "unknown")

        # Infer parent from pending_agent_dispatch
        parent_id = "main"
        if session.get("pending_agent_dispatch"):
            parent_id = session["pending_agent_dispatch"]
            session["pending_agent_dispatch"] = None

        session["agents"][sub_id] = {
            "agent_id": sub_id,
            "agent_type": sub_type,
            "parent_id": parent_id,
            "status": "running",
            "tool_calls": [],
            "started_at": now,
            "ended_at": None,
        }

    elif event_name == "SubagentStop":
        sub_id = data.get("agent_id", "")
        if sub_id in session["agents"]:
            agent = session["agents"][sub_id]
            agent["status"] = "done"
            agent["ended_at"] = now

    elif event_name == "PreToolUse":
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})
        tool_use_id = data.get("tool_use_id", f"tu-{now}")

        # If main agent is calling Agent tool, record for parent inference
        if tool_name == "Agent" and agent_id == "main":
            session["pending_agent_dispatch"] = "main"
        elif tool_name == "Agent" and agent_id != "main":
            session["pending_agent_dispatch"] = agent_id

        # Track skills
        if tool_name == "Skill":
            skill_name = tool_input.get("skill", tool_input.get("name", "unknown"))
            # Avoid duplicates
            existing = [s["name"] for s in session["skills"]]
            if skill_name not in existing:
                session["skills"].append({"name": skill_name, "invoked_at": now, "agent_id": agent_id})

        # Track tasks
        if tool_name == "TaskCreate":
            task_id = f"task-{len(session['tasks']) + 1}"
            session["tasks"][task_id] = {
                "task_id": task_id,
                "subject": tool_input.get("subject", ""),
                "description": tool_input.get("description", ""),
                "status": "pending",
                "created_at": now,
                "updated_at": now,
                "agent_id": agent_id,
                "operations": [],
            }
        elif tool_name == "TaskUpdate":
            tid = tool_input.get("taskId", "")
            # Match by taskId (could be "1", "2", etc.)
            match_key = None
            for k, t in session["tasks"].items():
                if k == tid or k == f"task-{tid}" or t["task_id"] == tid:
                    match_key = k
                    break
            if match_key:
                task = session["tasks"][match_key]
                if tool_input.get("status"):
                    task["status"] = tool_input["status"]
                if tool_input.get("subject"):
                    task["subject"] = tool_input["subject"]
                if tool_input.get("description"):
                    task["description"] = tool_input["description"]
                task["updated_at"] = now

        # Link tool calls to the current in-progress task
        if tool_name not in ("TaskCreate", "TaskUpdate", "TaskGet", "TaskList", "Skill"):
            for t in session["tasks"].values():
                if t["status"] == "in_progress":
                    t["operations"].append({
                        "tool_name": tool_name,
                        "summary": _tool_short_summary(tool_name, tool_input),
                        "at": now,
                        "agent_id": agent_id,
                    })

        # Track context for audit
        track_context(session, agent_id, tool_name, tool_input)

        # Check duplicate
        is_dup, dup_of = check_duplicate(session, agent_id, tool_name, tool_input)
        event["_is_duplicate"] = is_dup
        event["_duplicate_of"] = dup_of
        event["tool_name"] = tool_name
        event["tool_input"] = tool_input
        event["agent_id"] = agent_id

        tc = {
            "tool_use_id": tool_use_id,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "agent_id": agent_id,
            "started_at": now,
            "ended_at": None,
            "is_duplicate": is_dup,
            "duplicate_of": dup_of,
        }
        session["tool_calls"][tool_use_id] = tc
        if agent_id in session["agents"]:
            session["agents"][agent_id]["tool_calls"].append(tool_use_id)

    elif event_name == "PostToolUse":
        tool_use_id = data.get("tool_use_id", "")
        if tool_use_id in session["tool_calls"]:
            tc = session["tool_calls"][tool_use_id]
            tc["ended_at"] = now
        event["agent_id"] = agent_id
        event["tool_name"] = data.get("tool_name", "")

    session["events"].append(event)
    return event


# ---------------------------------------------------------------------------
# SSE broadcast
# ---------------------------------------------------------------------------

async def broadcast(event: dict):
    msg = json.dumps(event, default=str, ensure_ascii=False)
    dead = []
    for q in sse_queues:
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        sse_queues.remove(q)


# ---------------------------------------------------------------------------
# HTTP Handlers
# ---------------------------------------------------------------------------

async def handle_event(request: web.Request) -> web.Response:
    """Receive hook events from Claude Code."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)

    event = process_event(data)
    await broadcast(event)
    return web.json_response({"ok": True})


async def handle_sessions(request: web.Request) -> web.Response:
    """List all sessions."""
    result = []
    for s in sessions.values():
        result.append({
            "session_id": s["session_id"],
            "cwd": s["cwd"],
            "status": s["status"],
            "started_at": s["started_at"],
            "agents_count": len(s["agents"]),
            "events_count": len(s["events"]),
            "metrics": compute_metrics(s),
        })
    result.sort(key=lambda x: x["started_at"], reverse=True)
    return web.json_response(result)


async def handle_session_detail(request: web.Request) -> web.Response:
    """Get full session data."""
    sid = request.match_info["sid"]
    if sid not in sessions:
        return web.json_response({"error": "not found"}, status=404)

    s = sessions[sid]
    agents_list = []
    for a in s["agents"].values():
        aid = a["agent_id"]
        # Get tool call details for this agent
        tc_details = []
        for tu_id in a["tool_calls"]:
            tc = s["tool_calls"].get(tu_id, {})
            tc_details.append({
                "tool_use_id": tc.get("tool_use_id", ""),
                "tool_name": tc.get("tool_name", ""),
                "tool_input": tc.get("tool_input", {}),
                "started_at": tc.get("started_at"),
                "ended_at": tc.get("ended_at"),
                "is_duplicate": tc.get("is_duplicate", False),
                "duplicate_of": tc.get("duplicate_of"),
            })

        # Context audit for subagents
        context_audit = None
        if a["parent_id"]:
            context_audit = compute_context_audit(s, aid)

        agents_list.append({
            "agent_id": aid,
            "agent_type": a["agent_type"],
            "parent_id": a["parent_id"],
            "status": a["status"],
            "tool_calls_count": len(a["tool_calls"]),
            "tool_calls": tc_details,
            "started_at": a["started_at"],
            "ended_at": a["ended_at"],
            "context_audit": context_audit,
        })

    # Build clean event list
    events_list = []
    for e in s["events"]:
        events_list.append({
            "hook_event_name": e.get("hook_event_name", ""),
            "received_at": e.get("received_at", 0),
            "agent_id": e.get("agent_id", "main"),
            "tool_name": e.get("tool_name", ""),
            "tool_input": e.get("tool_input", {}),
            "_is_duplicate": e.get("_is_duplicate", False),
            "_duplicate_of": e.get("_duplicate_of"),
            "agent_type": e.get("agent_type", ""),
        })

    # Tasks list
    tasks_list = []
    for t in s["tasks"].values():
        tasks_list.append({
            "task_id": t["task_id"],
            "subject": t["subject"],
            "description": t["description"],
            "status": t["status"],
            "created_at": t["created_at"],
            "updated_at": t["updated_at"],
            "agent_id": t.get("agent_id", "main"),
            "operations": t.get("operations", [])[-50:],  # last 50
        })

    return web.json_response({
        "session_id": s["session_id"],
        "cwd": s["cwd"],
        "status": s["status"],
        "started_at": s["started_at"],
        "agents": agents_list,
        "events": events_list,
        "metrics": compute_metrics(s),
        "skills": s.get("skills", []),
        "tasks": tasks_list,
    })


async def handle_sse(request: web.Request) -> web.StreamResponse:
    """Server-Sent Events stream."""
    response = web.StreamResponse()
    response.headers["Content-Type"] = "text/event-stream"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Access-Control-Allow-Origin"] = "*"
    await response.prepare(request)

    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    sse_queues.append(queue)

    try:
        while True:
            msg = await queue.get()
            await response.write(f"data: {msg}\n\n".encode())
    except (asyncio.CancelledError, ConnectionResetError):
        pass
    finally:
        if queue in sse_queues:
            sse_queues.remove(queue)

    return response


async def handle_index(request: web.Request) -> web.Response:
    """Serve dashboard HTML."""
    html_path = Path(__file__).parent / "dashboard.html"
    if not html_path.exists():
        return web.Response(text="dashboard.html not found", status=404)
    return web.FileResponse(html_path)


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/events", handle_event)
    app.router.add_get("/api/sessions", handle_sessions)
    app.router.add_get("/api/session/{sid}", handle_session_detail)
    app.router.add_get("/stream", handle_sse)
    app.router.add_get("/", handle_index)
    # Serve prototype files too
    app.router.add_static("/static/", Path(__file__).parent, show_index=True)
    return app


def main():
    parser = argparse.ArgumentParser(description="Claude Code Monitor Server")
    parser.add_argument("--port", type=int, default=1010, help="Port (default: 1010)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host (default: 0.0.0.0)")
    args = parser.parse_args()

    app = create_app()
    print(f"Claude Code Monitor starting on http://{args.host}:{args.port}")
    print(f"Dashboard: http://{args.host}:{args.port}/")
    print(f"Hook endpoint: http://{args.host}:{args.port}/events")
    web.run_app(app, host=args.host, port=args.port, print=None)


if __name__ == "__main__":
    main()
