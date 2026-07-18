#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path


TARGET_MODELS = frozenset({"gpt-5.6-sol", "gpt-5.6-terra"})
TARGET_SOURCES = frozenset({"startup", "compact"})
PROMPT_FILES = (
    "compaction-continuity.md",
    "subagent-orchestration.md",
)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"codex-long-task-continuity: invalid hook input: {exc}", file=sys.stderr)
        return 1
    if not isinstance(event, dict):
        print("codex-long-task-continuity: hook input must be a JSON object", file=sys.stderr)
        return 1

    if event.get("hook_event_name") != "SessionStart":
        return 0
    if event.get("model") not in TARGET_MODELS:
        return 0
    if event.get("source") not in TARGET_SOURCES:
        return 0

    codex_home = Path(__file__).resolve().parent.parent
    prompt_dir = codex_home / "prompt-overlays"
    try:
        parts = [(prompt_dir / name).read_text(encoding="utf-8") for name in PROMPT_FILES]
    except OSError as exc:
        print(f"codex-long-task-continuity: unable to read prompt overlay: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write("\n\n".join(part.rstrip() for part in parts) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
