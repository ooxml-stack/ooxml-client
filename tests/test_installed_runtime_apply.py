"""Real `ooxml apply` subprocess contracts against the installed dev runtime.

These tests pin the U02/U11 ledger regressions on the installed package at
``~/.local/ooxml-dev/OOXML`` and gate the fixed build. They skip when no dev
runtime is installed (CI has none); on a dev machine they run the real binary
end to end, per the repository rule that mock responses alone do not prove
document behavior.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

RUNTIME_HOME = Path.home() / ".local/ooxml-dev/OOXML"
OOXML = RUNTIME_HOME / "bin" / "ooxml"
OOXML_ENGINE = RUNTIME_HOME / "bin" / "ooxml-engine"

TEXT_REPLACE_ROWS = [
    {"operation_id": "text.replace", "target": "slides[0].shapes[0]",
     "params": {"find": "Test", "replace": "Alpha"}},
    {"operation_id": "text.replace", "target": "slides[0].shapes[0]",
     "params": {"find": "Alpha", "replace": "Beta"}},
]


def _runtime_env() -> dict:
    env = dict(os.environ)
    home = Path.home()
    env.setdefault("OOXML_LICENSE_FILE", str(home / ".ooxml/dev-license-unstamped.json"))
    key = home / ".ooxml/dev-activation-public-key.txt"
    if key.is_file():
        env.setdefault("OOXML_LICENSE_PUBLIC_KEY", key.read_text().strip())
    env.setdefault("OOXML_RUNTIME_EXECUTABLE", str(OOXML_ENGINE))
    env["PATH"] = f"{RUNTIME_HOME / 'bin'}:{env.get('PATH', '')}"
    return env


def _error_message(output: str) -> str:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return output
    error = payload.get("error", {})
    runtime_error = error.get("runtime_error", {})
    if isinstance(runtime_error, dict) and "content" in runtime_error:
        return "".join(
            part.get("text", "") for part in runtime_error["content"] if isinstance(part, dict))
    return runtime_error.get("error", {}).get("message", output)


class InstalledRuntimeApplyTests(unittest.TestCase):
    """Ledger U02/U11 regressions must be observable through the real CLI."""

    def setUp(self):
        if not OOXML.is_file():
            self.skipTest("installed dev runtime not present")

    def _apply(self, params: dict) -> tuple[int, str, str]:
        done = subprocess.run(
            [str(OOXML), "apply", "--params", json.dumps(params)],
            capture_output=True, text=True, timeout=120, env=_runtime_env(),
        )
        return done.returncode, done.stdout, done.stderr

    def _snapshot(self, path: Path) -> str:
        done = subprocess.run(
            [str(OOXML), "inspect", "--params", json.dumps({"path": str(path)})],
            capture_output=True, text=True, timeout=120, env=_runtime_env(),
        )
        return json.loads(done.stdout)["snapshot_id"]

    def _seed_deck(self, folder: str) -> tuple[Path, Path]:
        deck, out = Path(folder) / "deck.pptx", Path(folder) / "deck-out.pptx"
        subprocess.run(
            [str(OOXML_ENGINE), "create", "pptx", str(deck)],
            check=True, capture_output=True, timeout=120, env=_runtime_env(),
        )
        self._apply({"path": str(deck), "operation_id": "slide.add",
                     "target": "presentation", "params": {}})
        self._apply({"path": str(deck), "operation_id": "shape.add_textbox",
                     "target": "slides[0]",
                     "params": {"left": 914400, "top": 914400, "width": 4572000,
                                "height": 914400, "text": "Test Slide"}})
        return deck, out

    def test_dict_plan_same_shape_rows_report_single_v3_observation(self):
        """U02: two text.replace rows on one shape still read back one V3 target."""
        with tempfile.TemporaryDirectory() as folder:
            deck, out = self._seed_deck(folder)
            plan = {
                "kind": "operation_plan", "version": "1.0", "format": "pptx",
                "input_snapshot_id": self._snapshot(deck),
                "transaction": "atomic", "operations": TEXT_REPLACE_ROWS,
            }
            code, stdout, _ = self._apply(
                {"path": str(deck), "output_path": str(out), "plan": plan})

            self.assertEqual(code, 0, stdout)
            receipt = json.loads(stdout)
            self.assertIs(receipt["success"], True)
            self.assertEqual(receipt["verification_level"], "V3")
            self.assertEqual(len(receipt["visible_observations"]), 1)
            self.assertEqual(receipt["visible_observations"][0]["target"], "slides[0].shapes[0]")
            self.assertEqual(receipt["observation_target_count"], 1)
            self.assertEqual(receipt["omitted_target_count"], 0)

    def test_workbook_create_dry_run_exits_zero_without_writing(self):
        """U11: dry-run create must return a schema-complete receipt, exit 0."""
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "dry-run.xlsx"
            code, stdout, stderr = self._apply(
                {"path": str(target), "operation_id": "workbook.create",
                 "target": "workbook", "params": {"sheet_name": "Demo"}, "dry_run": True})

            self.assertNotIn("checkpoint", stderr, stdout)
            self.assertEqual(code, 0, stderr)
            receipt = json.loads(stdout)
            self.assertIs(receipt["success"], True)
            self.assertEqual(receipt["save_status"], "not_saved")
            self.assertEqual(receipt["readback"]["checkpoint"], "operation_save")
            self.assertFalse(target.exists())

    def test_workbook_create_real_write_exits_zero_with_success_receipt(self):
        """U11: a real create must not fail after the file was written."""
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "created.xlsx"
            code, stdout, stderr = self._apply(
                {"path": str(target), "operation_id": "workbook.create",
                 "target": "workbook", "params": {"sheet_name": "Data"}})

            self.assertNotIn("checkpoint", stderr, stdout)
            self.assertEqual(code, 0, stderr)
            self.assertIs(json.loads(stdout)["success"], True)
            self.assertTrue(target.is_file())

    def test_create_refusals_match_presentation_create_messages(self):
        """Refusals exit non-zero before any write, with presentation.create text."""
        with tempfile.TemporaryDirectory() as folder:
            existing_xlsx = Path(folder) / "existing.xlsx"
            existing_xlsx.write_bytes(b"keep")
            code_x, _, err_x = self._apply(
                {"path": str(existing_xlsx), "operation_id": "workbook.create",
                 "target": "workbook", "params": {"sheet_name": "Demo"}})
            existing_pptx = Path(folder) / "existing.pptx"
            existing_pptx.write_bytes(b"keep")
            code_p, _, err_p = self._apply(
                {"path": str(existing_pptx), "operation_id": "presentation.create",
                 "target": "presentation", "params": {}})

            self.assertNotEqual(code_x, 0)
            self.assertNotEqual(code_p, 0)
            self.assertIn("refuses to overwrite an existing file", _error_message(err_x))
            self.assertIn("refuses to overwrite an existing file", _error_message(err_p))
            self.assertEqual(existing_xlsx.read_bytes(), b"keep")
            self.assertEqual(existing_pptx.read_bytes(), b"keep")

            wrong_x = Path(folder) / "wrong.docx"
            code_sx, _, err_sx = self._apply(
                {"path": str(wrong_x), "operation_id": "workbook.create",
                 "target": "workbook", "params": {"sheet_name": "Demo"}})
            wrong_p = Path(folder) / "wrong.xlsx"
            code_sp, _, err_sp = self._apply(
                {"path": str(wrong_p), "operation_id": "presentation.create",
                 "target": "presentation", "params": {}})

            self.assertNotEqual(code_sx, 0)
            self.assertNotEqual(code_sp, 0)
            self.assertIn("output_path must end with .xlsx", _error_message(err_sx))
            self.assertIn("output_path must end with .pptx", _error_message(err_sp))
            self.assertFalse(wrong_x.exists())
            self.assertFalse(wrong_p.exists())


if __name__ == "__main__":
    unittest.main()
