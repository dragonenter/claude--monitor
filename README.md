# Claude Code Monitor

基于 Claude Code 官方 Hooks 机制的实时监控仪表盘，可视化 Agent 执行流程、工具调用链路和效率指标。

![Dashboard](https://img.shields.io/badge/Status-Beta-blue) ![Python](https://img.shields.io/badge/Python-3.8+-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## 解决什么问题

当 Claude Code 处理复杂任务时，会派发多个 Subagent 并行工作。但这个过程对用户完全不透明：

- **重复工作**：Subagent 可能重复读取主 Agent 已经读过的文件
- **上下文丢失**：Subagent 没有收到主 Agent 已确认的决策信息
- **效率黑盒**：不知道 Token 花在了哪里，哪些工作是浪费的

Claude Code Monitor 让这一切可见。

## 功能特性

### 实时事件流
- 每次工具调用（Read、Grep、Edit、Bash 等）实时展示
- 自动标记重复调用（不同 Agent 对同一文件/模式的重复操作）
- 按时间顺序展示，标注所属 Agent

### 调用链追踪
- 树状展示 Agent 层级关系（Main → Subagent → 工具调用）
- 甘特图时间线，直观看到各 Agent 的工作时间分布
- 每个工具调用的耗时和参数完整展示

### 上下文审计
- 为每个 Subagent 计算「上下文完整度」评分（0-100%）
- 对比主 Agent 已知信息 vs Subagent 实际收到的信息
- 标记缺失的上下文（导致重复工作的根因）
- 展示派发 Subagent 时的原始 Prompt

### 多会话支持
- 同时监控多个 Claude Code 会话（不同项目目录）
- `claude -r` 恢复会话自动归组到同一项目
- 会话选择器快速切换

## 快速开始

### 1. 安装依赖

```bash
pip install aiohttp
```

### 2. 配置 Hooks

```bash
python3 install.py
```

这会自动在 `~/.claude/settings.json` 中添加监控所需的 Hooks 配置。

> 如需自定义端口：`python3 install.py --port 8080`

### 3. 启动监控服务

```bash
python3 server.py
```

默认监听 `0.0.0.0:1010`。

### 4. 打开仪表盘

浏览器访问：

```
http://localhost:1010
```

### 5. 正常使用 Claude Code

在任意目录启动 Claude Code：

```bash
claude "帮我实现用户认证模块"
```

仪表盘会自动实时显示所有事件。

## 项目结构

```
├── server.py          # 监控服务（接收 Hook 事件、SSE 推送、API）
├── dashboard.html     # 仪表盘前端（单文件，无构建依赖）
├── install.py         # Hooks 配置工具（安装/卸载/查看状态）
├── load_demo.py       # Demo 数据加载（用于测试和演示）
└── docs/              # 设计文档
```

## 工作原理

```
Claude Code (任意项目目录)
    │
    ├── Hook: SessionStart / SessionEnd
    ├── Hook: PreToolUse / PostToolUse
    ├── Hook: SubagentStart / SubagentStop
    │
    │  (通过 curl 将事件 POST 到监控服务)
    ▼
Monitor Server (server.py)
    ├── 接收事件，按 session_id 分组存储
    ├── 构建 Agent 树（通过时序推断父子关系）
    ├── 检测重复调用（同 pattern/file 被不同 Agent 调用）
    ├── 计算效率指标
    └── SSE 推送到浏览器
    │
    ▼
Dashboard (dashboard.html)
    ├── 事件流（实时 Feed）
    ├── 调用链追踪（Agent 树 + 时间线）
    └── 上下文审计（完整度评分 + 缺失分析）
```

所有数据来源均为 Claude Code 官方 Hooks 接口，不涉及任何逆向或私有 API。

## 常用命令

```bash
# 安装 hooks
python3 install.py

# 卸载 hooks
python3 install.py --uninstall

# 查看 hooks 状态
python3 install.py --status

# 启动服务（自定义端口）
python3 server.py --port 8080

# 加载演示数据（测试用）
NO_PROXY='*' python3 load_demo.py
```

## 注意事项

- 监控服务需要在 Claude Code 之前启动（或同时运行），否则早期事件会丢失
- 如果服务器有 HTTP 代理，demo 数据加载需要加 `NO_PROXY='*'` 前缀
- 数据存储在内存中，服务重启后清空
- Hooks 配置在 `~/.claude/settings.json` 中，对所有 Claude Code 会话生效

## 技术栈

- **后端**：Python + aiohttp（异步 HTTP 服务）
- **前端**：原生 HTML/CSS/JS + SSE（无框架依赖，无构建步骤）
- **数据采集**：Claude Code Hooks（command 类型，通过 curl 转发）
