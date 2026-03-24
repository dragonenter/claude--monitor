#!/usr/bin/env python3
"""Load demo data into the monitor server."""
import json
import urllib.request

URL = "http://127.0.0.1:1010/events"
SID = "demo-session-001"
CWD = "/data/codes/myproject"

def post(data):
    data.setdefault("session_id", SID)
    data.setdefault("cwd", CWD)
    body = json.dumps(data).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req)

events = [
    # Session start
    {"hook_event_name": "SessionStart"},

    # Main agent searches and reads
    {"hook_event_name": "PreToolUse", "tool_name": "Grep", "tool_input": {"pattern": "permission|role|auth", "path": "src/"}, "tool_use_id": "tu-001"},
    {"hook_event_name": "PostToolUse", "tool_name": "Grep", "tool_use_id": "tu-001"},
    {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "src/auth/middleware.ts"}, "tool_use_id": "tu-002"},
    {"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_use_id": "tu-002"},
    {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "src/models/user.ts"}, "tool_use_id": "tu-003"},
    {"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_use_id": "tu-003"},

    # Main dispatches Explore subagent
    {"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": {"prompt": "Analyze the existing permission architecture in the codebase"}, "tool_use_id": "tu-004"},
    {"hook_event_name": "SubagentStart", "agent_id": "agent-explore-1", "agent_type": "Explore"},

    # Explore subagent: DUPLICATE grep + read
    {"hook_event_name": "PreToolUse", "tool_name": "Grep", "tool_input": {"pattern": "permission|role|auth", "path": "src/"}, "tool_use_id": "tu-005", "agent_id": "agent-explore-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Grep", "tool_use_id": "tu-005", "agent_id": "agent-explore-1"},
    {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "src/auth/middleware.ts"}, "tool_use_id": "tu-006", "agent_id": "agent-explore-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_use_id": "tu-006", "agent_id": "agent-explore-1"},
    # Explore finds new file
    {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "src/routes/admin.ts"}, "tool_use_id": "tu-007", "agent_id": "agent-explore-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_use_id": "tu-007", "agent_id": "agent-explore-1"},
    {"hook_event_name": "SubagentStop", "agent_id": "agent-explore-1", "agent_type": "Explore"},
    {"hook_event_name": "PostToolUse", "tool_name": "Agent", "tool_use_id": "tu-004"},

    # Main dispatches Plan subagent
    {"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": {"prompt": "Design RBAC implementation plan using casbin library"}, "tool_use_id": "tu-008"},
    {"hook_event_name": "SubagentStart", "agent_id": "agent-plan-1", "agent_type": "Plan"},
    {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "package.json"}, "tool_use_id": "tu-009", "agent_id": "agent-plan-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_use_id": "tu-009", "agent_id": "agent-plan-1"},
    {"hook_event_name": "PreToolUse", "tool_name": "Grep", "tool_input": {"pattern": "express|koa|fastify", "path": "package.json"}, "tool_use_id": "tu-009b", "agent_id": "agent-plan-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Grep", "tool_use_id": "tu-009b", "agent_id": "agent-plan-1"},
    {"hook_event_name": "SubagentStop", "agent_id": "agent-plan-1", "agent_type": "Plan"},
    {"hook_event_name": "PostToolUse", "tool_name": "Agent", "tool_use_id": "tu-008"},

    # Main dispatches Implementation subagent (missing plan context!)
    {"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": {"prompt": "Implement Role and Permission models for RBAC"}, "tool_use_id": "tu-010"},
    {"hook_event_name": "SubagentStart", "agent_id": "agent-impl-1", "agent_type": "general"},
    # Impl subagent: MORE duplicates
    {"hook_event_name": "PreToolUse", "tool_name": "Grep", "tool_input": {"pattern": "permission|role|auth", "path": "src/"}, "tool_use_id": "tu-011", "agent_id": "agent-impl-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Grep", "tool_use_id": "tu-011", "agent_id": "agent-impl-1"},
    {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "src/models/user.ts"}, "tool_use_id": "tu-012", "agent_id": "agent-impl-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_use_id": "tu-012", "agent_id": "agent-impl-1"},
    {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "src/auth/middleware.ts"}, "tool_use_id": "tu-012b", "agent_id": "agent-impl-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_use_id": "tu-012b", "agent_id": "agent-impl-1"},
    {"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {"file_path": "src/models/role.ts", "content": "custom RBAC impl"}, "tool_use_id": "tu-013", "agent_id": "agent-impl-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_use_id": "tu-013", "agent_id": "agent-impl-1"},
    {"hook_event_name": "PreToolUse", "tool_name": "Edit", "tool_input": {"file_path": "src/auth/middleware.ts"}, "tool_use_id": "tu-014", "agent_id": "agent-impl-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Edit", "tool_use_id": "tu-014", "agent_id": "agent-impl-1"},
    {"hook_event_name": "SubagentStop", "agent_id": "agent-impl-1", "agent_type": "general"},
    {"hook_event_name": "PostToolUse", "tool_name": "Agent", "tool_use_id": "tu-010"},

    # Main runs tests
    {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "npm test"}, "tool_use_id": "tu-015"},
    {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_use_id": "tu-015"},
]

for e in events:
    post(e)

print(f"Loaded {len(events)} events")

# Verify
resp = urllib.request.urlopen("http://127.0.0.1:1010/api/sessions")
data = json.loads(resp.read())
s = data[0]
m = s["metrics"]
print(f"Session: {s['session_id']}")
print(f"  Agents: {s['agents_count']}, Events: {s['events_count']}")
print(f"  Tool calls: {m['tool_calls']}, Duplicates: {m['duplicates']}, Efficiency: {m['efficiency']}%")
