# Project Index

| Path | Status | Purpose | Public | Notes |
|---|---|---|---|---|
| `README.md` | `active` | Complete Hook architecture, Agent installation, migration, validation, old-session boundary, trust, and rollback guide | Yes | Designed to be handed directly to an Agent with the GitHub URL |
| `install.py` | `active` | Backup-first structured install, verify, uninstall, and manifest restore CLI | Yes | Python 3.9+, standard library only; does not modify `config.toml` or model catalogs |
| `hooks/session_start_overlay.py` | `active` | SessionStart model/source filter and developer-context output | Yes | Exact allowlist: Sol/Terra; exact sources: startup/compact |
| `prompts/compaction-continuity.md` | `active` | Compaction continuation state, current delegation authorization, and Completion gate | Yes | Installed as an independent developer-context overlay; later user instructions supersede earlier authorization state |
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
- Current local branch: `main`
- V1 public baseline: `a0b97d46db55734c0a7476ac03d2b6a9af337efd`
- V2 implementation commit: `2db5c60f312679a1ee83df537c3525a3b654af4a`
- V2 publication status: published to public `main`; `git ls-remote` matched the implementation commit and the remote README matched the local file byte-for-byte
- Published README SHA-256: `ae516411089871148570892ccef992861d7ff0bef4f8823522be00045299e021`
