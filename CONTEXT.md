# Project Context

## Purpose

Publish a self-contained Codex `SessionStart` Hook that an Agent can install safely from the GitHub repository. The Hook adds two developer-context overlays only for GPT-5.6 Sol and Terra:

1. Long-task compaction continuity with a Completion gate.
2. Root-agent sub-agent orchestration, context propagation, verification, and progressive reasoning-effort selection.

## Current State

- The old model-catalog and full `root_agent_usage_hint_text` replacement method is superseded.
- `README.md` is the public handoff and installation guide.
- `install.py` performs backup-first, structured `hooks.json` merge, idempotent upgrade, static verification, uninstall, and exact manifest restore.
- The Hook preserves Codex-managed official model, root, child-agent, tool, and multi-agent-mode prompts.
- Model scope is exactly `gpt-5.6-sol` and `gpt-5.6-terra`; Luna, GPT-5.5, and other models receive no overlay.
- The matcher is `startup|compact`. The README explicitly records that compact reinjection occurs after the current summary and cannot retroactively protect the first compaction of an old, uninjected session.
- Legacy full-root and model-catalog overlays are detected but not automatically removed because those files may contain unrelated user routing.
- The publication candidate passes 21 isolated tests, Python compilation, end-to-end install/idempotence/uninstall/restore exercise, and independent read-only QA with no remaining release blocker.
- Personal paths, local hashes, backups, logs, and unrelated `system-tools` records remain excluded from the public repository.
- Public repository: `https://github.com/hututuo/codex-long-task-continuity`.

## Handoff

Read `README.md` first. Run `python3 -m unittest discover -s tests -v` before changing installation behavior. V2 validation evidence is in `runs/20260718-130756_hook-installer-v2-publication/`; run artifacts remain ignored by Git, while public source state is indexed in `PROJECT_INDEX.md`.
