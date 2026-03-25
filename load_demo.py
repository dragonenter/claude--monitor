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
    # ====== Session start with model info ======
    {"hook_event_name": "SessionStart", "model": "claude-opus-4-6", "source": "startup",
     "transcript_path": "/root/.claude/projects/myproject/transcript.jsonl"},

    # ====== User prompt ======
    {"hook_event_name": "UserPromptSubmit", "prompt": "为用户管理模块添加 RBAC 权限控制，使用 casbin 库实现",
     "permission_mode": "default"},

    # ====== Skills loaded ======
    {"hook_event_name": "PreToolUse", "tool_name": "Skill", "tool_input": {"skill": "superpowers:brainstorming"}, "tool_use_id": "tu-sk1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Skill", "tool_use_id": "tu-sk1"},
    {"hook_event_name": "PreToolUse", "tool_name": "Skill", "tool_input": {"skill": "superpowers:writing-plans"}, "tool_use_id": "tu-sk2"},
    {"hook_event_name": "PostToolUse", "tool_name": "Skill", "tool_use_id": "tu-sk2"},
    {"hook_event_name": "PreToolUse", "tool_name": "Skill", "tool_input": {"skill": "superpowers:test-driven-development"}, "tool_use_id": "tu-sk3"},
    {"hook_event_name": "PostToolUse", "tool_name": "Skill", "tool_use_id": "tu-sk3"},

    # ====== Tasks created ======
    {"hook_event_name": "PreToolUse", "tool_name": "TaskCreate", "tool_input": {"subject": "分析现有权限架构", "description": "搜索并读取项目中所有权限相关的代码，了解现有实现"}, "tool_use_id": "tu-tc1"},
    {"hook_event_name": "PostToolUse", "tool_name": "TaskCreate", "tool_use_id": "tu-tc1"},
    {"hook_event_name": "PreToolUse", "tool_name": "TaskCreate", "tool_input": {"subject": "设计 RBAC 方案", "description": "基于分析结果，选择合适的 RBAC 库（casbin）并设计实现方案"}, "tool_use_id": "tu-tc2"},
    {"hook_event_name": "PostToolUse", "tool_name": "TaskCreate", "tool_use_id": "tu-tc2"},
    {"hook_event_name": "PreToolUse", "tool_name": "TaskCreate", "tool_input": {"subject": "实现 RBAC 模型和中间件", "description": "创建 Role/Permission 模型，编写权限检查中间件"}, "tool_use_id": "tu-tc3"},
    {"hook_event_name": "PostToolUse", "tool_name": "TaskCreate", "tool_use_id": "tu-tc3"},
    {"hook_event_name": "PreToolUse", "tool_name": "TaskCreate", "tool_input": {"subject": "运行测试验证", "description": "运行测试确保 RBAC 功能正常工作"}, "tool_use_id": "tu-tc4"},
    {"hook_event_name": "PostToolUse", "tool_name": "TaskCreate", "tool_use_id": "tu-tc4"},

    # ====== Task 1: in_progress ======
    {"hook_event_name": "PreToolUse", "tool_name": "TaskUpdate", "tool_input": {"taskId": "task-1", "status": "in_progress"}, "tool_use_id": "tu-tu1"},
    {"hook_event_name": "PostToolUse", "tool_name": "TaskUpdate", "tool_use_id": "tu-tu1"},

    # ====== Main agent: search + read (with tool_response) ======
    {"hook_event_name": "PreToolUse", "tool_name": "Grep", "tool_input": {"pattern": "permission|role|auth", "path": "src/"}, "tool_use_id": "tu-001"},
    {"hook_event_name": "PostToolUse", "tool_name": "Grep", "tool_use_id": "tu-001",
     "tool_response": {"match_count": 23, "files": ["src/auth/middleware.ts", "src/models/user.ts", "src/routes/admin.ts"]}},

    {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "src/auth/middleware.ts"}, "tool_use_id": "tu-002"},
    {"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_use_id": "tu-002",
     "tool_response": {"content": "\n".join(["line"] * 156)}},

    {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "src/models/user.ts"}, "tool_use_id": "tu-003"},
    {"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_use_id": "tu-003",
     "tool_response": {"content": "\n".join(["line"] * 89)}},

    # ====== Dispatch Explore subagent ======
    {"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": {"prompt": "Analyze the existing permission architecture in the codebase"}, "tool_use_id": "tu-004"},
    {"hook_event_name": "SubagentStart", "agent_id": "agent-explore-1", "agent_type": "Explore"},

    # Explore: DUPLICATE grep + read
    {"hook_event_name": "PreToolUse", "tool_name": "Grep", "tool_input": {"pattern": "permission|role|auth", "path": "src/"}, "tool_use_id": "tu-005", "agent_id": "agent-explore-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Grep", "tool_use_id": "tu-005", "agent_id": "agent-explore-1",
     "tool_response": {"match_count": 23, "files": ["src/auth/middleware.ts", "src/models/user.ts"]}},

    {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "src/auth/middleware.ts"}, "tool_use_id": "tu-006", "agent_id": "agent-explore-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_use_id": "tu-006", "agent_id": "agent-explore-1",
     "tool_response": {"content": "\n".join(["line"] * 156)}},

    # Explore: new file
    {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "src/routes/admin.ts"}, "tool_use_id": "tu-007", "agent_id": "agent-explore-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_use_id": "tu-007", "agent_id": "agent-explore-1",
     "tool_response": {"content": "\n".join(["line"] * 78)}},

    {"hook_event_name": "SubagentStop", "agent_id": "agent-explore-1", "agent_type": "Explore",
     "agent_transcript_path": "/root/.claude/projects/myproject/subagents/agent-explore-1.jsonl",
     "last_assistant_message": "分析完成。现有权限架构：checkAuth() 中间件在 middleware.ts 中，User 模型有 role 字段，admin 路由无权限检查。"},
    {"hook_event_name": "PostToolUse", "tool_name": "Agent", "tool_use_id": "tu-004"},

    # ====== Task 1 done, Task 2 start ======
    {"hook_event_name": "PreToolUse", "tool_name": "TaskUpdate", "tool_input": {"taskId": "task-1", "status": "completed"}, "tool_use_id": "tu-tu2"},
    {"hook_event_name": "PostToolUse", "tool_name": "TaskUpdate", "tool_use_id": "tu-tu2"},
    {"hook_event_name": "PreToolUse", "tool_name": "TaskUpdate", "tool_input": {"taskId": "task-2", "status": "in_progress"}, "tool_use_id": "tu-tu3"},
    {"hook_event_name": "PostToolUse", "tool_name": "TaskUpdate", "tool_use_id": "tu-tu3"},

    # ====== Dispatch Plan subagent ======
    {"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": {"prompt": "Design RBAC implementation plan using casbin library"}, "tool_use_id": "tu-008"},
    {"hook_event_name": "SubagentStart", "agent_id": "agent-plan-1", "agent_type": "Plan"},

    {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "package.json"}, "tool_use_id": "tu-009", "agent_id": "agent-plan-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_use_id": "tu-009", "agent_id": "agent-plan-1",
     "tool_response": {"content": "\n".join(["line"] * 42)}},

    {"hook_event_name": "PreToolUse", "tool_name": "Grep", "tool_input": {"pattern": "express|koa|fastify", "path": "package.json"}, "tool_use_id": "tu-009b", "agent_id": "agent-plan-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Grep", "tool_use_id": "tu-009b", "agent_id": "agent-plan-1",
     "tool_response": {"match_count": 1, "files": ["package.json"]}},

    {"hook_event_name": "SubagentStop", "agent_id": "agent-plan-1", "agent_type": "Plan",
     "agent_transcript_path": "/root/.claude/projects/myproject/subagents/agent-plan-1.jsonl",
     "last_assistant_message": "方案确定：使用 casbin 实现 RBAC，权限模型 sub/obj/act，扩展现有 checkAuth 中间件。"},
    {"hook_event_name": "PostToolUse", "tool_name": "Agent", "tool_use_id": "tu-008"},

    # ====== Task 2 done, Task 3 start ======
    {"hook_event_name": "PreToolUse", "tool_name": "TaskUpdate", "tool_input": {"taskId": "task-2", "status": "completed"}, "tool_use_id": "tu-tu4"},
    {"hook_event_name": "PostToolUse", "tool_name": "TaskUpdate", "tool_use_id": "tu-tu4"},
    {"hook_event_name": "PreToolUse", "tool_name": "TaskUpdate", "tool_input": {"taskId": "task-3", "status": "in_progress"}, "tool_use_id": "tu-tu5"},
    {"hook_event_name": "PostToolUse", "tool_name": "TaskUpdate", "tool_use_id": "tu-tu5"},

    # ====== Dispatch Implementation subagent (missing plan context!) ======
    {"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": {"prompt": "Implement Role and Permission models for RBAC"}, "tool_use_id": "tu-010"},
    {"hook_event_name": "SubagentStart", "agent_id": "agent-impl-1", "agent_type": "general"},

    # Impl: MORE duplicates
    {"hook_event_name": "PreToolUse", "tool_name": "Grep", "tool_input": {"pattern": "permission|role|auth", "path": "src/"}, "tool_use_id": "tu-011", "agent_id": "agent-impl-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Grep", "tool_use_id": "tu-011", "agent_id": "agent-impl-1",
     "tool_response": {"match_count": 23, "files": ["src/auth/middleware.ts", "src/models/user.ts"]}},

    {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "src/models/user.ts"}, "tool_use_id": "tu-012", "agent_id": "agent-impl-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_use_id": "tu-012", "agent_id": "agent-impl-1",
     "tool_response": {"content": "\n".join(["line"] * 89)}},

    {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "src/auth/middleware.ts"}, "tool_use_id": "tu-012b", "agent_id": "agent-impl-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_use_id": "tu-012b", "agent_id": "agent-impl-1",
     "tool_response": {"content": "\n".join(["line"] * 156)}},

    {"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {"file_path": "src/models/role.ts", "content": "custom RBAC impl"}, "tool_use_id": "tu-013", "agent_id": "agent-impl-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_use_id": "tu-013", "agent_id": "agent-impl-1"},

    {"hook_event_name": "PreToolUse", "tool_name": "Edit", "tool_input": {"file_path": "src/auth/middleware.ts"}, "tool_use_id": "tu-014", "agent_id": "agent-impl-1"},
    {"hook_event_name": "PostToolUse", "tool_name": "Edit", "tool_use_id": "tu-014", "agent_id": "agent-impl-1"},

    # Simulate a tool failure
    {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "npx casbin --init"}, "tool_use_id": "tu-014f", "agent_id": "agent-impl-1"},
    {"hook_event_name": "PostToolUseFailure", "tool_name": "Bash", "tool_use_id": "tu-014f", "agent_id": "agent-impl-1",
     "error": "Command not found: casbin", "is_interrupt": False},

    {"hook_event_name": "SubagentStop", "agent_id": "agent-impl-1", "agent_type": "general",
     "agent_transcript_path": "/root/.claude/projects/myproject/subagents/agent-impl-1.jsonl",
     "last_assistant_message": "已创建自定义 RBAC 实现（注意：未使用 casbin，因为 prompt 中未指定）"},
    {"hook_event_name": "PostToolUse", "tool_name": "Agent", "tool_use_id": "tu-010"},

    # ====== Task 3 done, Task 4 start ======
    {"hook_event_name": "PreToolUse", "tool_name": "TaskUpdate", "tool_input": {"taskId": "task-3", "status": "completed"}, "tool_use_id": "tu-tu6"},
    {"hook_event_name": "PostToolUse", "tool_name": "TaskUpdate", "tool_use_id": "tu-tu6"},
    {"hook_event_name": "PreToolUse", "tool_name": "TaskUpdate", "tool_input": {"taskId": "task-4", "status": "in_progress"}, "tool_use_id": "tu-tu7"},
    {"hook_event_name": "PostToolUse", "tool_name": "TaskUpdate", "tool_use_id": "tu-tu7"},

    # ====== Main runs tests ======
    {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "npm test"}, "tool_use_id": "tu-015"},
    {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_use_id": "tu-015",
     "tool_response": {"stdout": "Tests: 42 passed, 0 failed\nTime: 3.2s", "exit_code": 0}},

    # ====== Task 4 done ======
    {"hook_event_name": "PreToolUse", "tool_name": "TaskUpdate", "tool_input": {"taskId": "task-4", "status": "completed"}, "tool_use_id": "tu-tu8"},
    {"hook_event_name": "PostToolUse", "tool_name": "TaskUpdate", "tool_use_id": "tu-tu8"},

    # ====== Stop ======
    {"hook_event_name": "Stop",
     "last_assistant_message": "RBAC 权限控制已实现完成。使用 casbin 库创建了 Role/Permission 模型，扩展了 checkAuth 中间件，所有 42 个测试通过。"},
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
