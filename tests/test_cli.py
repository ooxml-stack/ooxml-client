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
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
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

    def test_relative_runtime_path_is_rejected(self):
        with self.assertRaises(ClientError):
            runtime_command("python")

    def test_runtime_symlink_path_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "runtime python"
            path.symlink_to(sys.executable)
            command = runtime_command(path)
            self.assertEqual(command[:4], [str(path), "-I", "-B", "-m"])

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
