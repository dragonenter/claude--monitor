#!/usr/bin/env python3
"""Auto-configure Claude Code hooks for the monitoring dashboard.

Adds HTTP hooks to Claude Code settings.json so that tool calls and
agent events are sent to the monitor server.

Usage:
    python3 install.py              # install hooks (default port 1010)
    python3 install.py --port 8080  # custom port
    python3 install.py --uninstall  # remove hooks
"""

import argparse
import json
import os
import sys
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
SETTINGS_FILE = CLAUDE_DIR / "settings.json"

HOOK_EVENTS = [
    "SessionStart",
    "SessionEnd",
    "PreToolUse",
    "PostToolUse",
    "SubagentStart",
    "SubagentStop",
]

HOOK_MARKER = "claude-code-monitor"


def build_hooks(port: int) -> dict:
    """Build hook configuration for all monitored events."""
    url = f"http://127.0.0.1:{port}/events"
    # Claude Code requires: {"matcher": "...", "hooks": [...]}
    command = f"curl -s --noproxy '*' -X POST -H 'Content-Type: application/json' -d @- {url} || true"
    hooks = {}
    for event in HOOK_EVENTS:
        hooks[event] = [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": command,
                        "_marker": HOOK_MARKER,
                    }
                ],
            }
        ]
    return hooks


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    return {}


def save_settings(settings: dict):
    CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    print(f"Settings saved to {SETTINGS_FILE}")


def install_hooks(port: int):
    settings = load_settings()
    hooks = settings.get("hooks", {})

    # Remove old monitor hooks first
    for event in HOOK_EVENTS:
        if event in hooks:
            hooks[event] = [
                h for h in hooks[event]
                if not (isinstance(h, dict) and h.get("_marker") == HOOK_MARKER)
            ]

    # Add new hooks
    new_hooks = build_hooks(port)
    for event, hook_list in new_hooks.items():
        if event not in hooks:
            hooks[event] = []
        hooks[event].extend(hook_list)

    settings["hooks"] = hooks
    save_settings(settings)

    print(f"\nInstalled monitor hooks for events: {', '.join(HOOK_EVENTS)}")
    print(f"Events will POST to: http://127.0.0.1:{port}/events")
    print(f"\nStart the monitor server:")
    print(f"  python3 server.py --port {port}")
    print(f"\nThen use Claude Code normally. Open the dashboard at:")
    print(f"  http://localhost:{port}/")


def uninstall_hooks():
    settings = load_settings()
    hooks = settings.get("hooks", {})

    removed = 0
    for event in HOOK_EVENTS:
        if event in hooks:
            before = len(hooks[event])
            new_list = []
            for entry in hooks[event]:
                # Check if any inner hook has our marker
                inner_hooks = entry.get("hooks", [])
                has_marker = any(
                    isinstance(h, dict) and h.get("_marker") == HOOK_MARKER
                    for h in inner_hooks
                )
                if not has_marker:
                    new_list.append(entry)
            hooks[event] = new_list
            removed += before - len(new_list)
            if not hooks[event]:
                del hooks[event]

    if not hooks:
        if "hooks" in settings:
            del settings["hooks"]

    save_settings(settings)
    print(f"Removed {removed} monitor hooks.")


def show_status():
    settings = load_settings()
    hooks = settings.get("hooks", {})

    print("Claude Code Monitor Hook Status")
    print("=" * 40)

    found = False
    for event in HOOK_EVENTS:
        event_hooks = hooks.get(event, [])
        monitor_hooks = [h for h in event_hooks if isinstance(h, dict) and h.get("_marker") == HOOK_MARKER]
        if monitor_hooks:
            found = True
            url = monitor_hooks[0].get("url", "?")
            print(f"  {event}: {url}")

    if not found:
        print("  No monitor hooks installed.")
        print(f"\n  Run: python3 install.py")


def main():
    parser = argparse.ArgumentParser(description="Configure Claude Code Monitor hooks")
    parser.add_argument("--port", type=int, default=1010, help="Monitor server port (default: 1010)")
    parser.add_argument("--uninstall", action="store_true", help="Remove monitor hooks")
    parser.add_argument("--status", action="store_true", help="Show current hook status")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.uninstall:
        uninstall_hooks()
    else:
        install_hooks(args.port)


if __name__ == "__main__":
    main()
