# Project Index

| Path | Status | Purpose | Public | Notes |
|---|---|---|---|---|
| `README.md` | `active` | Complete Hook architecture, Agent installation, migration, validation, old-session boundary, trust, and rollback guide | Yes | Designed to be handed directly to an Agent with the GitHub URL |
| `install.py` | `active` | Backup-first structured install, verify, uninstall, and manifest restore CLI | Yes | Python 3.9+, standard library only; does not modify `config.toml` or model catalogs |
| `hooks/session_start_overlay.py` | `active` | SessionStart model/source filter and developer-context output | Yes | Exact allowlist: Sol/Terra; exact sources: startup/compact |
| `prompts/compaction-continuity.md` | `active` | Compaction continuation state and Completion gate | Yes | Installed as an independent developer-context overlay |
| `prompts/subagent-orchestration.md` | `active` | Selective delegation, context propagation, verification, and reasoning levels | Yes | Medium majority, progressive high/xhigh, rare max |
| `tests/test_install.py` | `active` | Installer, scope, migration, idempotence, uninstall, restore, and failure tests | Yes | Uses isolated temporary Codex homes only |
| `LICENSE` | `active` | Apache License 2.0 | Yes | Project license |
| `NOTICE.md` | `active` | Upstream interface attribution and independent-project notice | Yes | No frozen official prompt copy remains |
| `CONTEXT.md` | `active` | Project purpose and handoff state | Yes | Contains no private machine state |
| `runs/20260715-000851_initial-publication/` | `reference` | Initial v1 publication and validation evidence | No | Git-ignored; v1 model-catalog/root override design is superseded |
| `runs/20260718-130756_hook-installer-v2-publication/` | `run` | V2 test, isolated install, idempotence, uninstall, restore, and independent QA evidence | No | Git-ignored; 21 tests and final strict isolated verification passed |

## Publication

- Remote: `https://github.com/hututuo/codex-long-task-continuity`
- Visibility: public
- Default branch: `main`
- Current local work branch: `feature/hook-installer-v2`
- V1 public baseline: `a0b97d46db55734c0a7476ac03d2b6a9af337efd`
- V2 publication status: validated on the task branch; pending merge, push, and remote readback
