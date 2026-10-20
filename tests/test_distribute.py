"""Distribution commands: skill installation and MCP registration shapes."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ooxml_client import distribute
from ooxml_client.cli import main


class InstallSkillTests(unittest.TestCase):
    def test_explicit_target_is_written(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "skill" / "SKILL.md"
            result = distribute.install_skill(target)
            self.assertTrue(target.is_file())
            self.assertEqual(result["skill"], str(target.resolve()))

    def test_existing_target_is_refused_without_force(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "SKILL.md"
            target.write_text("old", encoding="utf-8")
            with self.assertRaises(ValueError):
                distribute.install_skill(target)
            self.assertEqual(target.read_text(encoding="utf-8"), "old")

    def test_force_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "SKILL.md"
            target.write_text("old", encoding="utf-8")
            distribute.install_skill(target, force=True)
            self.assertNotEqual(target.read_text(encoding="utf-8"), "old")

    def test_default_target_requires_claude_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "no-claude" / "skills"
            with patch.object(distribute, "CLAUDE_SKILLS", missing):
                with self.assertRaises(ValueError):
                    distribute.install_skill()


class RegisterTests(unittest.TestCase):
    def test_claude_dry_run_prints_command_without_executing(self):
        with (
            patch.object(distribute.shutil, "which", return_value="/fake/claude"),
            patch.object(distribute, "_claude_listed", return_value=False),
        ):
            result = distribute.register_claude(dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["command"][0], "/fake/claude")
        self.assertIn("ooxml", result["command"])
        self.assertEqual(result["command"][-1], "core")

    def test_runtime_python_is_carried_into_the_registration(self):
        with (
            patch.object(distribute.shutil, "which", return_value="/fake/claude"),
            patch.object(distribute, "_claude_listed", return_value=False),
        ):
            result = distribute.register_claude(dry_run=True, runtime_python="/abs/bin/python")
        self.assertIn("--runtime-python=/abs/bin/python", result["command"])

    def test_native_runtime_is_carried_into_the_registration(self):
        with (
            patch.object(distribute.shutil, "which", return_value="/fake/claude"),
            patch.object(distribute, "_claude_listed", return_value=False),
        ):
            result = distribute.register_claude(dry_run=True, runtime_executable="/abs/ooxml-engine")
        self.assertIn("--runtime-executable=/abs/ooxml-engine", result["command"])

    def test_claude_missing_binary_fails(self):
        with patch.object(distribute.shutil, "which", return_value=None):
            with self.assertRaises(ValueError):
                distribute.register_claude(dry_run=True)

    def test_claude_existing_server_is_refused(self):
        with (
            patch.object(distribute.shutil, "which", return_value="/fake/claude"),
            patch.object(distribute, "_claude_listed", return_value=True),
        ):
            with self.assertRaises(ValueError):
                distribute.register_claude()

    def test_codex_block_escapes_windows_launchers(self):
        block = distribute._codex_block([r"C:\Users\dev\bin\ooxml.exe"])
        self.assertIn('command = "C:\\\\Users\\\\dev\\\\bin\\\\ooxml.exe"', block)
        block2 = distribute._codex_block(["/abs/bin/ooxml"])
        self.assertNotIn("\\\\", block2)

    def test_claude_listed_matches_only_the_exact_server_name(self):
        listed = distribute._claude_listed

        class Run:
            def __init__(self, stdout):
                self.stdout = stdout

        with (
            patch.object(distribute.shutil, "which", return_value="/fake/claude"),
            patch.object(distribute.subprocess, "run", return_value=Run("ooxml-foo (local)\nother-server\n")),
        ):
            self.assertFalse(listed("/fake/claude"))
        with (
            patch.object(distribute.shutil, "which", return_value="/fake/claude"),
            patch.object(distribute.subprocess, "run", return_value=Run("ooxml (local)\n")),
        ):
            self.assertTrue(listed("/fake/claude"))

    def test_codex_appends_block_and_refuses_duplicate(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "config.toml"
            with (
                patch.object(distribute, "CODEX_CONFIG", config),
                patch.object(distribute.shutil, "which", return_value=None),
            ):
                result = distribute.register_codex()
                text = config.read_text(encoding="utf-8")
                self.assertIn("[mcp_servers.ooxml]", text)
                self.assertIn("command", text)
                self.assertIn("args", text)
                self.assertEqual(result["config"], str(config))
                with self.assertRaises(ValueError):
                    distribute.register_codex()
                distribute.register_codex(force=True)
                self.assertEqual(text.count("[mcp_servers.ooxml]"), 1)


class CliWiringTests(unittest.TestCase):
    def test_install_skill_via_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "SKILL.md"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["install-skill", "--target", str(target)])
            self.assertEqual(code, 0)
            self.assertTrue(target.is_file())
            self.assertIn("skill", json.loads(output.getvalue()))

    def test_register_dry_run_via_cli(self):
        output = io.StringIO()
        with (
            patch.object(distribute.shutil, "which", return_value="/fake/claude"),
            patch.object(distribute, "_claude_listed", return_value=False),
            contextlib.redirect_stdout(output),
        ):
            code = main(["register", "claude", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output.getvalue())["dry_run"])

    def test_collision_exits_with_code_two(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "SKILL.md"
            target.write_text("old", encoding="utf-8")
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                code = main(["install-skill", "--target", str(target)])
            self.assertEqual(code, 2)
            self.assertIn("skill_exists", errors.getvalue())


class ActivateTests(unittest.TestCase):
    def test_activate_copies_license_into_place(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "acme.lic"
            source.write_text('{"licensee": "Acme"}', encoding="utf-8")
            with patch.object(distribute, "LICENSE_DIR", Path(folder) / "state"):
                result = distribute.activate(source)
            target = Path(folder) / "state" / "license.json"
            self.assertEqual(result["license"], str(target.resolve()))
            self.assertIn("Acme", target.read_text(encoding="utf-8"))

    def test_activate_refuses_missing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                distribute.activate(Path(folder) / "nope.lic")

    def test_activate_via_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "acme.lic"
            source.write_text("{}", encoding="utf-8")
            with patch.object(distribute, "LICENSE_DIR", Path(folder) / "state"):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = main(["activate", "--license", str(source)])
            self.assertEqual(code, 0)
            self.assertIn("license.json", out.getvalue())


if __name__ == "__main__":
    unittest.main()
