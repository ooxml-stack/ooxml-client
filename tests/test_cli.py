"""CLI result handling and runtime selection boundaries."""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ooxml_client.cli import main
from ooxml_client.errors import ClientError
from ooxml_client.runtime import runtime_command


class CliTests(unittest.TestCase):
    def test_missing_runtime_is_a_nonzero_json_error(self):
        output, errors = io.StringIO(), io.StringIO()
        with (
            patch.dict(os.environ, {}, clear=True),
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(errors),
        ):
            code = main(["man"])
        self.assertEqual(code, 1)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(json.loads(errors.getvalue())["error"]["kind"], "runtime_not_configured")

    def test_params_file_and_returned_facts_are_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            params = {"path": "file with spaces.xlsx", "target": "Summary!B2"}
            path = Path(folder) / "params.json"
            path.write_text(json.dumps(params))
            output = io.StringIO()
            with patch("ooxml_client.cli.Client") as factory, contextlib.redirect_stdout(output):
                factory.return_value.call.return_value = {"value": 42, "readback": "unavailable"}
                code = main(["view", "--params-file", str(path)])
            factory.return_value.call.assert_called_once_with("ooxml_view", params)
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue()), {"value": 42, "readback": "unavailable"})

    def test_nonobject_parameters_fail_without_launch(self):
        with patch("ooxml_client.cli.Client") as factory, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["view", "--params", "[]"]), 2)
        factory.return_value.call.assert_not_called()

    def test_strict_validate_exits_nonzero_on_failed_validation(self):
        result = {"passed": False, "status": "failed", "findings": [{}], "rules_run": 3}
        output, errors = io.StringIO(), io.StringIO()
        with (
            patch("ooxml_client.cli.Client") as factory,
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(errors),
        ):
            factory.return_value.call.return_value = result
            code = main(["validate", "--params", '{"path": "a.docx", "level": "semantic"}', "--strict"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue()), result)
        self.assertIn("failure", errors.getvalue())

    def test_strict_validate_keeps_passing_results_at_exit_zero(self):
        result = {"passed": True, "status": "passed", "findings": [], "rules_run": 3}
        output = io.StringIO()
        with (
            patch("ooxml_client.cli.Client") as factory,
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            factory.return_value.call.return_value = result
            code = main(["validate", "--params", '{"path": "a.docx"}', "--strict"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue()), result)

    def test_strict_validate_failures_reported_by_status_only(self):
        result = {"status": "failed", "findings": [{}]}
        errors = io.StringIO()
        with (
            patch("ooxml_client.cli.Client") as factory,
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(errors),
        ):
            factory.return_value.call.return_value = result
            code = main(["validate", "--params", '{"path": "a.docx"}', "--strict"])
        self.assertEqual(code, 1)

    def test_validate_without_strict_keeps_the_completed_call_contract(self):
        result = {"passed": False, "status": "failed", "findings": [{}]}
        output = io.StringIO()
        with (
            patch("ooxml_client.cli.Client") as factory,
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            factory.return_value.call.return_value = result
            code = main(["validate", "--params", '{"path": "a.docx"}'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue()), result)

    def test_relative_runtime_path_is_rejected(self):
        with self.assertRaises(ClientError):
            runtime_command("python")

    def test_runtime_symlink_path_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "runtime python"
            path.symlink_to(sys.executable)
            command = runtime_command(path)
            self.assertEqual(command[:4], [str(path), "-I", "-B", "-m"])

    def test_native_runtime_path_is_preserved_and_uses_serve_stdio(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "ooxml-engine"
            path.symlink_to(sys.executable)
            command = runtime_command(runtime_executable=path)
            self.assertEqual(command, [str(path), "serve", "--transport", "stdio"])

    def test_unconfigured_runtime_is_not_auto_discovered_beside_python(self):
        with tempfile.TemporaryDirectory() as folder:
            executable = Path(folder) / "python"
            executable.symlink_to(sys.executable)
            sibling = Path(folder) / "ooxml-engine"
            sibling.symlink_to(sys.executable)
            with (
                patch("sys.executable", str(executable)),
                patch.dict(os.environ, {}, clear=True),
                self.assertRaises(ClientError) as ctx,
            ):
                runtime_command()
        self.assertEqual(ctx.exception.kind, "runtime_not_configured")

    def test_native_runtime_environment_is_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "ooxml-engine"
            path.symlink_to(sys.executable)
            with patch.dict(os.environ, {"OOXML_RUNTIME_EXECUTABLE": str(path)}, clear=True):
                command = runtime_command()
            self.assertEqual(command[0], str(path))
            self.assertEqual(command[1:], ["serve", "--transport", "stdio"])

    def test_probe_uses_packaged_runtime_helper(self):
        with patch("ooxml_client.cli.run_probe", return_value={"tool_count": 8}) as probe:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["probe", "--profile", "core"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue()), {"tool_count": 8})
        probe.assert_called_once()

    def test_pdf_probe_returns_stable_unavailable_contract(self):
        from ooxml_client.probe import pdf_readability_contract

        result = pdf_readability_contract()
        self.assertEqual(result["profile"], "pdf")
        self.assertIn("available", result)
        if not result["available"]:
            self.assertEqual(result["error"]["code"], "pdf_readability_unavailable")

    def test_mcp_executes_the_real_server_without_tool_reimplementation(self):
        class Executed(Exception):
            pass

        with patch.dict(os.environ, {}, clear=True), patch("os.execv", side_effect=Executed) as execute:
            with self.assertRaises(Executed):
                main(["--runtime-python", sys.executable, "mcp", "--profile", "workflow"])
            args = execute.call_args.args
            self.assertEqual(args[1], [sys.executable, "-I", "-B", "-m", "ooxml_operation_engine.mcp_server"])
            self.assertEqual(os.environ["OOXML_MCP_PROFILE"], "workflow")


if __name__ == "__main__":
    unittest.main()


class ApplyExitCodeTests(unittest.TestCase):
    """A failed apply must be observable from the shell when explicitly requested."""

    def _run(self, result, extra):
        output, errors = io.StringIO(), io.StringIO()
        with (
            patch("ooxml_client.cli.Client") as factory,
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(errors),
        ):
            factory.return_value.call.return_value = result
            code = main(["apply", "--params", '{"path": "a.pptx"}', *extra])
        return code, output.getvalue(), errors.getvalue()

    def test_fail_on_failure_exits_nonzero_for_a_noop_receipt(self):
        result = {
            "success": False,
            "postconditions": {"require_change": {"passed": False, "no_op": True}},
        }
        code, stdout, stderr = self._run(result, ["--fail-on-failure"])
        self.assertEqual(code, 1)
        # The receipt is still printed so a caller can read why it failed.
        self.assertEqual(json.loads(stdout), result)
        self.assertIn("failure", stderr)

    def test_fail_on_failure_keeps_successful_applies_at_exit_zero(self):
        result = {"success": True, "save_status": "saved"}
        code, stdout, _ = self._run(result, ["--fail-on-failure"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout), result)

    def test_without_the_flag_a_failed_apply_still_exits_zero(self):
        result = {"success": False}
        code, stdout, _ = self._run(result, [])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout), result)


class ApplyPartialFailureTests(unittest.TestCase):
    """--fail-on-failure must catch partial plans and failed saves, not just success=false."""

    def _run(self, result):
        output, errors = io.StringIO(), io.StringIO()
        with (
            patch("ooxml_client.cli.Client") as factory,
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(errors),
        ):
            factory.return_value.call.return_value = result
            code = main(["apply", "--params", '{"path": "a.pptx"}', "--fail-on-failure"])
        return code, json.loads(output.getvalue()), errors.getvalue()

    def test_partial_plan_with_failed_count_exits_nonzero(self):
        code, receipt, stderr = self._run({"success": True, "failed_count": 1})
        self.assertEqual(code, 1)
        self.assertEqual(receipt["failed_count"], 1)
        self.assertIn("failure", stderr)

    def test_failed_save_exits_nonzero(self):
        code, _, stderr = self._run({"success": True, "save_status": "failed"})
        self.assertEqual(code, 1)
        self.assertIn("failure", stderr)

    def test_clean_result_exits_zero(self):
        code, _, _ = self._run({"success": True, "failed_count": 0, "save_status": "saved"})
        self.assertEqual(code, 0)

    def test_missing_failed_count_defaults_to_zero(self):
        code, _, _ = self._run({"success": True})
        self.assertEqual(code, 0)
