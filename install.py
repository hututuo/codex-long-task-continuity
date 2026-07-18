#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_HOOK = PROJECT_ROOT / "hooks" / "session_start_overlay.py"
SOURCE_PROMPTS = {
    "compaction-continuity.md": PROJECT_ROOT / "prompts" / "compaction-continuity.md",
    "subagent-orchestration.md": PROJECT_ROOT / "prompts" / "subagent-orchestration.md",
}
DEST_HOOK_NAME = "codex-long-task-continuity.py"
STATUS_MESSAGE = "Loading Codex long-task continuity rules"
MATCHER = "startup|compact"
TARGET_MODELS = ("gpt-5.6-sol", "gpt-5.6-terra")
NON_TARGET_MODELS = ("gpt-5.6-luna", "gpt-5.5")
LEGACY_STATUS_MESSAGE = "Loading task continuity rules"
BACKUP_VERSION = 1


class InstallError(RuntimeError):
    pass


def resolve_codex_home(raw: str | None) -> Path:
    if raw:
        return Path(raw).expanduser().resolve()
    env_home = os.environ.get("CODEX_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def destination_paths(codex_home: Path) -> dict[str, Path]:
    codex_home = codex_home.expanduser().resolve()
    paths = {
        "hooks.json": codex_home / "hooks.json",
        "hook": codex_home / "hooks" / DEST_HOOK_NAME,
    }
    for name in SOURCE_PROMPTS:
        paths[f"prompt:{name}"] = codex_home / "prompt-overlays" / name
    return paths


def lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(str(path.expanduser())))


def ensure_safe_targets(codex_home: Path, paths: Iterable[Path]) -> None:
    codex_home = codex_home.resolve()
    for path in paths:
        target = lexical_absolute(path)
        try:
            target.relative_to(codex_home)
        except ValueError as exc:
            raise InstallError(f"target escapes Codex home: {target}") from exc
        current = target
        while current != codex_home:
            if current.is_symlink():
                raise InstallError(f"refusing symlinked path inside Codex home: {current}")
            current = current.parent


def mode_differs(path: Path, expected_mode: int) -> bool:
    return os.name != "nt" and path.is_file() and (path.stat().st_mode & 0o777) != expected_mode


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json_object(path: Path, *, missing_ok: bool = False) -> dict[str, Any]:
    if missing_ok and not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InstallError(f"missing file: {path}") from exc
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise InstallError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise InstallError(f"expected a JSON object in {path}")
    return value


def atomic_write(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name != "nt":
            os.chmod(temporary_path, mode)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def command_for(script_path: Path) -> str:
    executable_names = ("python", "python3") if os.name == "nt" else ("python3",)
    python = next(
        (Path(found).absolute() for name in executable_names if (found := shutil.which(name))),
        Path(sys.executable).absolute(),
    )
    if os.name == "nt":
        return subprocess.list2cmdline([str(python), str(script_path)])
    return f"{shlex.quote(str(python))} {shlex.quote(str(script_path))}"


def is_managed_handler(handler: Any, destination_hook: Path) -> bool:
    if not isinstance(handler, dict):
        return False
    status_message = handler.get("statusMessage")
    command = str(handler.get("command", ""))
    if str(destination_hook) in command:
        return True
    return status_message == LEGACY_STATUS_MESSAGE and "session-start-overlay.rb" in command


def is_managed_group(group: Any, destination_hook: Path) -> bool:
    if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
        return False
    return any(is_managed_handler(handler, destination_hook) for handler in group["hooks"])


def strip_managed_handlers(groups: list[Any], destination_hook: Path) -> tuple[list[Any], int]:
    retained_groups: list[Any] = []
    removed = 0
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
            retained_groups.append(group)
            continue
        handlers = group["hooks"]
        retained_handlers = [
            handler for handler in handlers if not is_managed_handler(handler, destination_hook)
        ]
        removed += len(handlers) - len(retained_handlers)
        if retained_handlers:
            retained_group = json.loads(json.dumps(group))
            retained_group["hooks"] = retained_handlers
            retained_groups.append(retained_group)
    return retained_groups, removed


def merged_hooks_document(current: dict[str, Any], destination_hook: Path) -> tuple[dict[str, Any], int]:
    candidate = json.loads(json.dumps(current))
    hooks = candidate.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise InstallError("hooks.json field 'hooks' must be an object")
    groups = hooks.setdefault("SessionStart", [])
    if not isinstance(groups, list):
        raise InstallError("hooks.json field 'hooks.SessionStart' must be an array")

    retained, removed = strip_managed_handlers(groups, destination_hook)
    retained.append(
        {
            "matcher": MATCHER,
            "hooks": [
                {
                    "type": "command",
                    "command": command_for(destination_hook),
                    "statusMessage": STATUS_MESSAGE,
                }
            ],
        }
    )
    hooks["SessionStart"] = retained
    return candidate, removed


def without_managed_hook(current: dict[str, Any], destination_hook: Path) -> tuple[dict[str, Any], int]:
    candidate = json.loads(json.dumps(current))
    hooks = candidate.get("hooks")
    if not isinstance(hooks, dict):
        return candidate, 0
    groups = hooks.get("SessionStart")
    if not isinstance(groups, list):
        return candidate, 0
    retained, removed = strip_managed_handlers(groups, destination_hook)
    if retained:
        hooks["SessionStart"] = retained
    else:
        hooks.pop("SessionStart", None)
    if not hooks:
        candidate.pop("hooks", None)
    return candidate, removed


def next_backup_dir(codex_home: Path, action: str) -> Path:
    timestamp = dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    root = codex_home / "backups"
    candidate = root / f"codex-long-task-continuity-{timestamp}-{action}"
    suffix = 1
    while candidate.exists():
        candidate = root / f"codex-long-task-continuity-{timestamp}-{action}-{suffix}"
        suffix += 1
    return candidate


def create_backup(codex_home: Path, paths: Iterable[Path], action: str) -> Path:
    backup_dir = next_backup_dir(codex_home, action)
    files_dir = backup_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=False)
    entries = []
    for index, path in enumerate(paths):
        exists = path.is_file()
        entry: dict[str, Any] = {
            "target": str(path),
            "existed": exists,
            "mode": (path.stat().st_mode & 0o777) if exists else None,
            "sha256": sha256_bytes(path.read_bytes()) if exists else None,
            "backup": None,
        }
        if exists:
            backup_name = f"{index:02d}-{path.name}"
            backup_path = files_dir / backup_name
            shutil.copy2(path, backup_path)
            entry["backup"] = str(backup_path.relative_to(backup_dir))
        entries.append(entry)

    manifest = {
        "format_version": BACKUP_VERSION,
        "created_at": dt.datetime.now().astimezone().isoformat(),
        "action": action,
        "codex_home": str(codex_home),
        "files": entries,
    }
    atomic_write(
        backup_dir / "manifest.json",
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        0o600,
    )
    return backup_dir


def source_bytes() -> dict[str, bytes]:
    missing = [path for path in [SOURCE_HOOK, *SOURCE_PROMPTS.values()] if not path.is_file()]
    if missing:
        raise InstallError(f"repository is incomplete; missing: {', '.join(map(str, missing))}")
    result = {"hook": SOURCE_HOOK.read_bytes()}
    for name, path in SOURCE_PROMPTS.items():
        result[f"prompt:{name}"] = path.read_bytes()
    return result


def install(codex_home: Path) -> Path | None:
    codex_home = codex_home.expanduser().resolve()
    codex_home.mkdir(parents=True, exist_ok=True)
    paths = destination_paths(codex_home)
    ensure_safe_targets(codex_home, [*paths.values(), codex_home / "backups"])
    non_files = [path for path in paths.values() if path.exists() and not path.is_file()]
    if non_files:
        raise InstallError(
            "refusing to replace non-file install targets: " + ", ".join(map(str, non_files))
        )
    sources = source_bytes()
    current_hooks = read_json_object(paths["hooks.json"], missing_ok=True)
    candidate_hooks, _ = merged_hooks_document(current_hooks, paths["hook"])

    hooks_changed = candidate_hooks != current_hooks or mode_differs(paths["hooks.json"], 0o600)
    file_changes = [
        key
        for key, data in sources.items()
        if not paths[key].is_file()
        or paths[key].read_bytes() != data
        or mode_differs(paths[key], 0o700 if key == "hook" else 0o600)
    ]
    if not hooks_changed and not file_changes:
        return None

    backup = create_backup(codex_home, paths.values(), "install")
    for key, data in sources.items():
        atomic_write(paths[key], data, 0o700 if key == "hook" else 0o600)
    if hooks_changed:
        atomic_write(
            paths["hooks.json"],
            (json.dumps(candidate_hooks, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
            0o600,
        )
    return backup


def uninstall(codex_home: Path) -> Path | None:
    codex_home = codex_home.expanduser().resolve()
    paths = destination_paths(codex_home)
    ensure_safe_targets(codex_home, [*paths.values(), codex_home / "backups"])
    current_hooks = read_json_object(paths["hooks.json"], missing_ok=True)
    candidate_hooks, removed = without_managed_hook(current_hooks, paths["hook"])
    managed_files = [paths["hook"], *(paths[f"prompt:{name}"] for name in SOURCE_PROMPTS)]
    non_files = [path for path in managed_files if path.exists() and not path.is_file()]
    if non_files:
        raise InstallError(
            "refusing to remove non-file install targets: " + ", ".join(map(str, non_files))
        )
    existing_files = [path for path in managed_files if path.is_file()]
    if removed == 0 and not existing_files:
        return None

    backup = create_backup(codex_home, paths.values(), "uninstall")
    if candidate_hooks != current_hooks:
        if candidate_hooks:
            atomic_write(
                paths["hooks.json"],
                (json.dumps(candidate_hooks, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
                0o600,
            )
        elif paths["hooks.json"].exists():
            paths["hooks.json"].unlink()
    for path in existing_files:
        path.unlink()
    return backup


def restore_backup(backup_dir: Path, expected_codex_home: Path | None = None) -> None:
    backup_dir = backup_dir.expanduser().resolve()
    manifest_path = backup_dir / "manifest.json"
    if manifest_path.is_symlink():
        raise InstallError(f"refusing symlinked backup manifest: {manifest_path}")
    manifest = read_json_object(manifest_path)
    if manifest.get("format_version") != BACKUP_VERSION:
        raise InstallError("unsupported backup manifest version")
    files = manifest.get("files")
    if not isinstance(files, list):
        raise InstallError("backup manifest does not contain a file list")
    raw_codex_home = manifest.get("codex_home")
    if not isinstance(raw_codex_home, str):
        raise InstallError("backup manifest does not contain a Codex home")
    codex_home = Path(raw_codex_home).expanduser().resolve()
    if expected_codex_home is not None and codex_home != expected_codex_home.resolve():
        raise InstallError(
            f"backup belongs to {codex_home}, not requested Codex home {expected_codex_home.resolve()}"
        )

    ensure_safe_targets(codex_home, [codex_home / "backups", *destination_paths(codex_home).values()])
    backup_root = (codex_home / "backups").resolve()
    try:
        backup_dir.relative_to(backup_root)
    except ValueError as exc:
        raise InstallError(f"backup directory is outside {backup_root}: {backup_dir}") from exc

    expected_targets = {
        lexical_absolute(path) for path in destination_paths(codex_home).values()
    }
    raw_targets = [
        entry.get("target") if isinstance(entry, dict) else None for entry in files
    ]
    if any(not isinstance(target, str) for target in raw_targets):
        raise InstallError("invalid backup manifest target list")
    manifest_targets = [lexical_absolute(Path(target)) for target in raw_targets]
    if len(manifest_targets) != len(expected_targets) or set(manifest_targets) != expected_targets:
        raise InstallError("backup manifest targets do not match this project's managed files")

    operations: list[tuple[Path, bytes | None, int | None]] = []
    for entry in files:
        if not isinstance(entry, dict) or not isinstance(entry.get("target"), str):
            raise InstallError("invalid backup manifest entry")
        target = lexical_absolute(Path(entry["target"]))
        if entry.get("existed"):
            relative_backup = entry.get("backup")
            if not isinstance(relative_backup, str):
                raise InstallError(f"backup payload missing for {target}")
            relative_path = Path(relative_backup)
            if (
                relative_path.is_absolute()
                or len(relative_path.parts) != 2
                or relative_path.parts[0] != "files"
                or ".." in relative_path.parts
            ):
                raise InstallError(f"invalid backup payload path: {relative_backup}")
            payload_root = backup_dir / "files"
            source = payload_root / relative_path.name
            if payload_root.is_symlink() or source.is_symlink():
                raise InstallError(f"refusing symlinked backup payload: {source}")
            if not source.is_file():
                raise InstallError(f"backup payload is missing or not a file: {source}")
            data = source.read_bytes()
            expected_hash = entry.get("sha256")
            if expected_hash and sha256_bytes(data) != expected_hash:
                raise InstallError(f"backup hash mismatch for {source}")
            mode = entry.get("mode") if isinstance(entry.get("mode"), int) else 0o600
            operations.append((target, data, mode))
        else:
            if target.exists() and not target.is_file():
                raise InstallError(f"refusing to remove non-file target: {target}")
            operations.append((target, None, None))

    for target, data, mode in operations:
        if data is not None and mode is not None:
            atomic_write(target, data, mode)
        elif target.exists():
            target.unlink()


def find_legacy_overrides(codex_home: Path) -> list[str]:
    warnings = []
    config_path = codex_home / "config.toml"
    if config_path.is_file():
        config_text = config_path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"(?m)^\s*root_agent_usage_hint_text\s*=", config_text):
            warnings.append(f"legacy full root prompt override found in {config_path}")

    catalog_paths = [codex_home / "gpt-5.5-routed-model-catalog.json"]
    if config_path.is_file():
        match = re.search(r'(?m)^\s*model_catalog_json\s*=\s*["\']([^"\']+)["\']', config_text)
        if match:
            configured = Path(os.path.expandvars(match.group(1))).expanduser()
            if not configured.is_absolute():
                configured = codex_home / configured
            catalog_paths.append(configured)

    seen = set()
    for catalog_path in catalog_paths:
        resolved = catalog_path.resolve()
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        try:
            catalog = read_json_object(resolved)
        except InstallError as exc:
            warnings.append(str(exc))
            continue
        models = catalog.get("models")
        if not isinstance(models, list):
            continue
        for model in models:
            if not isinstance(model, dict) or model.get("slug") != "gpt-5.6-sol":
                continue
            base = model.get("base_instructions")
            if isinstance(base, str) and "## Compaction continuity" in base:
                warnings.append(f"legacy model-catalog compaction overlay found in {resolved}")
            break
    return warnings


def run_installed_hook(script: Path, model: str, source: str) -> subprocess.CompletedProcess[str]:
    payload = {
        "hook_event_name": "SessionStart",
        "session_id": "continuity-verification",
        "transcript_path": None,
        "cwd": str(PROJECT_ROOT),
        "model": model,
        "permission_mode": "default",
        "source": source,
    }
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


def verify(codex_home: Path) -> tuple[list[str], list[str]]:
    codex_home = codex_home.expanduser().resolve()
    failures = []
    warnings = find_legacy_overrides(codex_home)
    paths = destination_paths(codex_home)
    sources = source_bytes()

    for key, expected in sources.items():
        target = paths[key]
        if not target.is_file():
            failures.append(f"missing installed file: {target}")
        elif target.read_bytes() != expected:
            failures.append(f"installed file differs from repository source: {target}")
        elif os.name != "nt":
            expected_mode = 0o700 if key == "hook" else 0o600
            actual_mode = target.stat().st_mode & 0o777
            if actual_mode != expected_mode:
                failures.append(
                    f"unexpected mode for {target}: {actual_mode:04o}, expected {expected_mode:04o}"
                )

    try:
        hooks = read_json_object(paths["hooks.json"])
        if os.name != "nt":
            hooks_mode = paths["hooks.json"].stat().st_mode & 0o777
            if hooks_mode != 0o600:
                failures.append(
                    f"unexpected mode for {paths['hooks.json']}: {hooks_mode:04o}, expected 0600"
                )
        groups = hooks.get("hooks", {}).get("SessionStart", [])
        managed = [group for group in groups if is_managed_group(group, paths["hook"])]
        if len(managed) != 1:
            failures.append(f"expected one managed SessionStart group, found {len(managed)}")
        elif managed[0].get("matcher") != MATCHER:
            failures.append(f"unexpected matcher: {managed[0].get('matcher')!r}")
        else:
            managed_handlers = [
                handler
                for handler in managed[0].get("hooks", [])
                if is_managed_handler(handler, paths["hook"])
            ]
            if len(managed_handlers) != 1:
                failures.append(
                    f"expected one managed SessionStart handler, found {len(managed_handlers)}"
                )
            else:
                handler = managed_handlers[0]
                if handler.get("type") != "command":
                    failures.append(f"unexpected hook handler type: {handler.get('type')!r}")
                expected_command = command_for(paths["hook"])
                if handler.get("command") != expected_command:
                    failures.append(
                        f"unexpected hook command: {handler.get('command')!r}; expected {expected_command!r}"
                    )
    except (InstallError, AttributeError) as exc:
        failures.append(str(exc))

    if paths["hook"].is_file():
        for model in TARGET_MODELS:
            for source in ("startup", "compact"):
                result = run_installed_hook(paths["hook"], model, source)
                if result.returncode != 0:
                    failures.append(f"hook failed for {model}/{source}: {result.stderr.strip()}")
                    continue
                if result.stdout.count("## Compaction continuity") != 1:
                    failures.append(f"compaction prompt count failed for {model}/{source}")
                if result.stdout.count("## Sub-agent use") != 1:
                    failures.append(f"sub-agent prompt count failed for {model}/{source}")
        for model in NON_TARGET_MODELS:
            result = run_installed_hook(paths["hook"], model, "startup")
            if result.returncode != 0 or result.stdout:
                failures.append(f"non-target model received output: {model}")
        resume = run_installed_hook(paths["hook"], TARGET_MODELS[0], "resume")
        if resume.returncode != 0 or resume.stdout:
            failures.append("resume unexpectedly emitted developer context")

    return failures, warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install and verify the Codex long-task continuity SessionStart hook."
    )
    parser.add_argument(
        "--codex-home",
        help="Codex home directory. Defaults to CODEX_HOME or ~/.codex.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("install", help="Back up and install or upgrade the hook.")
    verify_parser = subparsers.add_parser("verify", help="Verify files, hook scope, and legacy conflicts.")
    verify_parser.add_argument(
        "--strict-legacy",
        action="store_true",
        help="Return a failure when legacy prompt overrides are detected.",
    )
    subparsers.add_parser("uninstall", help="Back up and remove only files managed by this project.")
    restore_parser = subparsers.add_parser("restore", help="Restore one backup manifest exactly.")
    restore_parser.add_argument("backup_dir", help="Backup directory created by this installer.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    codex_home = resolve_codex_home(args.codex_home)
    try:
        if args.command == "install":
            backup = install(codex_home)
            if backup is None:
                print("Already installed; no files changed.")
            else:
                print(f"Installed. Backup: {backup}")
            print("Next: open /hooks in Codex, review and trust the hook, then run verify.")
            return 0
        if args.command == "verify":
            failures, warnings = verify(codex_home)
            for warning in warnings:
                print(f"WARNING: {warning}")
            for failure in failures:
                print(f"ERROR: {failure}", file=sys.stderr)
            if failures:
                return 1
            if warnings and args.strict_legacy:
                return 2
            print("Verification passed: Sol/Terra receive both prompts; Luna/GPT-5.5 receive neither.")
            return 0
        if args.command == "uninstall":
            backup = uninstall(codex_home)
            if backup is None:
                print("Not installed; no files changed.")
            else:
                print(f"Uninstalled. Backup: {backup}")
            return 0
        if args.command == "restore":
            restore_backup(Path(args.backup_dir), codex_home)
            print(f"Restored backup: {Path(args.backup_dir).expanduser().resolve()}")
            return 0
    except (InstallError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
