from __future__ import annotations

import json
import importlib.util
import tempfile
import unittest
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import install


HOOK_SPEC = importlib.util.spec_from_file_location(
    "continuity_hook",
    install.SOURCE_HOOK,
)
assert HOOK_SPEC is not None and HOOK_SPEC.loader is not None
continuity_hook = importlib.util.module_from_spec(HOOK_SPEC)
HOOK_SPEC.loader.exec_module(continuity_hook)


class RepositoryDocumentationTests(unittest.TestCase):
    def test_readme_relative_links_resolve(self) -> None:
        readme = (install.PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme)
        relative_links = [
            link
            for link in links
            if not re.match(r"^[a-z][a-z0-9+.-]*:", link, flags=re.IGNORECASE)
            and not link.startswith("#")
        ]
        self.assertTrue(relative_links)
        for link in relative_links:
            self.assertTrue((install.PROJECT_ROOT / link).is_file(), link)

    def test_readme_describes_hook_delivery_without_frozen_prompt_overrides(self) -> None:
        readme = (install.PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        for marker in (
            "startup|compact",
            "gpt-5.6-sol",
            "gpt-5.6-terra",
            "gpt-5.6-luna",
            "gpt-5.5",
            "Completion gate",
            "python3 install.py install",
            "/hooks",
        ):
            self.assertIn(marker, readme)
        self.assertNotIn('root_agent_usage_hint_text = """', readme)
        self.assertNotIn('model_catalog_json = "', readme)


class InstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.codex_home = Path(self.temporary.name) / "codex-home"
        self.codex_home.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_hooks(self, document: dict) -> None:
        (self.codex_home / "hooks.json").write_text(
            json.dumps(document, indent=2) + "\n",
            encoding="utf-8",
        )

    def read_hooks(self) -> dict:
        return json.loads((self.codex_home / "hooks.json").read_text(encoding="utf-8"))

    def test_install_is_idempotent_and_preserves_unrelated_hooks(self) -> None:
        unrelated = {
            "matcher": "^Bash$",
            "hooks": [{"type": "command", "command": "check-bash"}],
        }
        self.write_hooks({"hooks": {"PreToolUse": [unrelated]}})

        backup = install.install(self.codex_home)
        self.assertIsNotNone(backup)
        document = self.read_hooks()
        self.assertEqual(document["hooks"]["PreToolUse"], [unrelated])
        self.assertEqual(len(document["hooks"]["SessionStart"]), 1)

        failures, warnings = install.verify(self.codex_home)
        self.assertEqual(failures, [])
        self.assertEqual(warnings, [])
        self.assertIsNone(install.install(self.codex_home))
        self.assertEqual(len(self.read_hooks()["hooks"]["SessionStart"]), 1)

    def test_installer_and_hook_scope_stay_in_sync(self) -> None:
        self.assertEqual(set(install.TARGET_MODELS), set(continuity_hook.TARGET_MODELS))
        self.assertEqual(set(continuity_hook.TARGET_SOURCES), {"startup", "compact"})

    def test_hook_command_prefers_stable_python_path(self) -> None:
        command = install.command_for(self.codex_home / "hook.py")
        if os.name != "nt" and shutil.which("python3"):
            self.assertEqual(shlex.split(command)[0], str(Path(shutil.which("python3")).absolute()))

    def test_install_replaces_known_legacy_hook_group(self) -> None:
        legacy = {
            "matcher": "startup|compact",
            "hooks": [
                {
                    "type": "command",
                    "command": "/usr/bin/ruby /tmp/session-start-overlay.rb",
                    "statusMessage": install.LEGACY_STATUS_MESSAGE,
                }
            ],
        }
        self.write_hooks({"hooks": {"SessionStart": [legacy]}})

        install.install(self.codex_home)
        groups = self.read_hooks()["hooks"]["SessionStart"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["matcher"], install.MATCHER)
        self.assertEqual(groups[0]["hooks"][0]["statusMessage"], install.STATUS_MESSAGE)

    def test_upgrade_preserves_unrelated_handler_in_same_group(self) -> None:
        destination = install.destination_paths(self.codex_home)["hook"]
        shared_group = {
            "matcher": "startup|compact",
            "hooks": [
                {
                    "type": "command",
                    "command": install.command_for(destination),
                    "statusMessage": install.STATUS_MESSAGE,
                },
                {"type": "command", "command": "keep-this-handler"},
            ],
        }
        self.write_hooks({"hooks": {"SessionStart": [shared_group]}})

        install.install(self.codex_home)
        groups = self.read_hooks()["hooks"]["SessionStart"]
        commands = [handler["command"] for group in groups for handler in group["hooks"]]
        self.assertIn("keep-this-handler", commands)
        self.assertEqual(sum(install.STATUS_MESSAGE in str(group) for group in groups), 1)

        install.uninstall(self.codex_home)
        groups = self.read_hooks()["hooks"]["SessionStart"]
        self.assertEqual(groups[0]["hooks"], [{"type": "command", "command": "keep-this-handler"}])

    def test_same_status_message_does_not_claim_an_unrelated_hook(self) -> None:
        collision = {
            "matcher": "startup",
            "hooks": [
                {
                    "type": "command",
                    "command": "unrelated-session-loader",
                    "statusMessage": install.STATUS_MESSAGE,
                }
            ],
        }
        self.write_hooks({"hooks": {"SessionStart": [collision]}})

        install.install(self.codex_home)
        groups = self.read_hooks()["hooks"]["SessionStart"]
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0], collision)

        install.uninstall(self.codex_home)
        self.assertEqual(self.read_hooks()["hooks"]["SessionStart"], [collision])

    def test_uninstall_preserves_unrelated_hooks_and_can_be_restored(self) -> None:
        unrelated = {
            "matcher": "manual|auto",
            "hooks": [{"type": "command", "command": "audit-compact"}],
        }
        self.write_hooks({"hooks": {"PreCompact": [unrelated]}})
        install.install(self.codex_home)

        uninstall_backup = install.uninstall(self.codex_home)
        self.assertIsNotNone(uninstall_backup)
        self.assertEqual(self.read_hooks(), {"hooks": {"PreCompact": [unrelated]}})
        paths = install.destination_paths(self.codex_home)
        self.assertFalse(paths["hook"].exists())

        install.restore_backup(uninstall_backup)
        failures, warnings = install.verify(self.codex_home)
        self.assertEqual(failures, [])
        self.assertEqual(warnings, [])

    def test_restore_rejects_a_different_codex_home(self) -> None:
        backup = install.install(self.codex_home)
        self.assertIsNotNone(backup)
        with self.assertRaises(install.InstallError):
            install.restore_backup(backup, self.codex_home / "different")

    def test_restore_validates_all_hashes_before_writing(self) -> None:
        original = {"hooks": {"Stop": [{"hooks": []}]}}
        self.write_hooks(original)
        backup = install.install(self.codex_home)
        self.assertIsNotNone(backup)
        installed_hooks = (self.codex_home / "hooks.json").read_bytes()
        manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
        payloads = [entry["backup"] for entry in manifest["files"] if entry["backup"]]
        self.assertTrue(payloads)
        (backup / payloads[-1]).write_bytes(b"corrupt")

        with self.assertRaises(install.InstallError):
            install.restore_backup(backup, self.codex_home)
        self.assertEqual((self.codex_home / "hooks.json").read_bytes(), installed_hooks)

    @unittest.skipIf(os.name == "nt", "symlink semantics differ on Windows")
    def test_install_refuses_symlinked_hooks_json(self) -> None:
        real_hooks = self.codex_home / "real-hooks.json"
        real_hooks.write_text("{}\n", encoding="utf-8")
        (self.codex_home / "hooks.json").symlink_to(real_hooks)
        with self.assertRaises(install.InstallError):
            install.install(self.codex_home)
        self.assertEqual(real_hooks.read_text(encoding="utf-8"), "{}\n")

    @unittest.skipIf(os.name == "nt", "symlink semantics differ on Windows")
    def test_install_refuses_symlinked_parent_directory(self) -> None:
        external = Path(self.temporary.name) / "external-hooks"
        external.mkdir()
        (self.codex_home / "hooks").symlink_to(external, target_is_directory=True)
        with self.assertRaises(install.InstallError):
            install.install(self.codex_home)
        self.assertEqual(list(external.iterdir()), [])

    @unittest.skipIf(os.name == "nt", "POSIX modes are not portable to Windows")
    def test_reinstall_repairs_file_modes(self) -> None:
        install.install(self.codex_home)
        hook = install.destination_paths(self.codex_home)["hook"]
        hook.chmod(0o644)
        backup = install.install(self.codex_home)
        self.assertIsNotNone(backup)
        self.assertEqual(hook.stat().st_mode & 0o777, 0o700)

    def test_restore_rejects_manifest_target_injection(self) -> None:
        backup = install.install(self.codex_home)
        self.assertIsNotNone(backup)
        manifest_path = backup / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"][0]["target"] = str(self.codex_home / "config.toml")
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(install.InstallError):
            install.restore_backup(backup, self.codex_home)
        self.assertFalse((self.codex_home / "config.toml").exists())

    def test_restore_rejects_payload_path_traversal(self) -> None:
        self.write_hooks({"hooks": {}})
        backup = install.install(self.codex_home)
        self.assertIsNotNone(backup)
        manifest_path = backup / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload_entry = next(entry for entry in manifest["files"] if entry["backup"])
        payload_entry["backup"] = "../manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(install.InstallError):
            install.restore_backup(backup, self.codex_home)

    def test_hook_rejects_non_object_json_without_traceback(self) -> None:
        result = subprocess.run(
            [sys.executable, str(install.SOURCE_HOOK)],
            input="[]",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be a JSON object", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_install_backup_restores_exact_preinstall_state(self) -> None:
        original = {
            "hooks": {
                "Stop": [{"hooks": [{"type": "command", "command": "done"}]}]
            }
        }
        self.write_hooks(original)
        backup = install.install(self.codex_home)
        self.assertIsNotNone(backup)

        install.restore_backup(backup)
        self.assertEqual(self.read_hooks(), original)
        paths = install.destination_paths(self.codex_home)
        self.assertFalse(paths["hook"].exists())
        for name in install.SOURCE_PROMPTS:
            self.assertFalse(paths[f"prompt:{name}"].exists())

    def test_verify_detects_legacy_prompt_overrides(self) -> None:
        (self.codex_home / "config.toml").write_text(
            'root_agent_usage_hint_text = "legacy"\n',
            encoding="utf-8",
        )
        catalog = {
            "models": [
                {
                    "slug": "gpt-5.6-sol",
                    "base_instructions": "official\n\n## Compaction continuity\nlegacy",
                }
            ]
        }
        (self.codex_home / "gpt-5.5-routed-model-catalog.json").write_text(
            json.dumps(catalog),
            encoding="utf-8",
        )
        install.install(self.codex_home)

        failures, warnings = install.verify(self.codex_home)
        self.assertEqual(failures, [])
        self.assertEqual(len(warnings), 2)

    def test_verify_rejects_tampered_hook_command(self) -> None:
        install.install(self.codex_home)
        document = self.read_hooks()
        document["hooks"]["SessionStart"][0]["hooks"][0]["command"] += " --unexpected"
        self.write_hooks(document)
        failures, _ = install.verify(self.codex_home)
        self.assertTrue(any("unexpected hook command" in failure for failure in failures))

    def test_invalid_hooks_json_is_never_overwritten(self) -> None:
        hooks_path = self.codex_home / "hooks.json"
        hooks_path.write_text("{invalid", encoding="utf-8")
        with self.assertRaises(install.InstallError):
            install.install(self.codex_home)
        self.assertEqual(hooks_path.read_text(encoding="utf-8"), "{invalid")
        self.assertFalse((self.codex_home / "backups").exists())


if __name__ == "__main__":
    unittest.main()
