# Project Context

## Purpose

Publish a self-contained guide that users can give directly to Codex so it can inspect, back up, merge, validate, and document two local prompt customizations:

1. GPT-5.6 long-task compaction continuity with a completion gate.
2. Root-agent sub-agent delegation, context propagation, verification, and reasoning-effort selection.

## Current State

- The public artifact is `README.md`.
- The README contains complete English prompt blocks, Chinese translations, a one-message automatic configuration workflow, manual configuration, validation, restart, rollback, limitations, and attribution.
- OpenAI Codex upstream was rechecked at `effd58d7505382f6b2d1736a4fc9e3eb90df1966`; the official 2,183-byte root prefix and eight-model catalog were unchanged from the preceding local snapshot.
- Personal paths, local hashes, backups, logs, and unrelated `system-tools` records are excluded from the public repository.
- This project does not itself modify `~/.codex/config.toml` or any installed model catalog.
- Public repository: `https://github.com/hututuo/codex-long-task-continuity`.
- Initial public commit `af715638a627cb5ccd1b19ab78ce2fc75e299126` and remote README blob `3a823a4b63cc412893186c2a085a9dd074f99739` were verified after push.

## Handoff

Read `README.md` first. Publication and validation evidence are indexed in `PROJECT_INDEX.md`; local run artifacts remain ignored by Git. The remote `main` branch is the public source of truth.
