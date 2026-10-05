"""Exercise the public MCP subprocess boundary without a private runtime."""

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from mcp.types import CallToolResult, TextContent

from ooxml_client import Client, ClientError, OperationError
from ooxml_client.transport import unpack

FIXTURE = Path(__file__).with_name("runtime_fixture.py")


def client(**kwargs):
    return Client(command=[sys.executable, str(FIXTURE)], **kwargs)


class ClientTests(unittest.TestCase):
    def test_round_trip_preserves_unicode_and_literal_shell_characters(self):
        params = {"path": "folder with spaces/file.docx", "text": "\u4e2d\u6587 $(exit 91) `exit 92`"}
        result = client().view(**params)
        self.assertEqual(result["params"], params)
        self.assertEqual(result["method"], "ooxml_view")

    def test_runtime_error_details_remain_intact(self):
        error = {"kind": "error", "error_kind": "stale_snapshot", "message": "Stale target",
                 "recovery": "rerun_discovery", "details": {"retry": False}}
        with self.assertRaises(OperationError) as ctx:
            client().apply(path="file.docx", _error=error)
        self.assertEqual(ctx.exception.error, error)
        self.assertEqual(ctx.exception.as_dict()["runtime_error"], error)

    def test_missing_runtime_never_imports_private_packages(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ClientError) as ctx:
            Client().man()
        self.assertEqual(ctx.exception.kind, "runtime_not_configured")
        self.assertNotIn("ooxml_operation_engine", sys.modules)

    def test_process_failure_does_not_claim_mutation_failure(self):
        with self.assertRaises(ClientError) as ctx:
            client().apply(_exit=True)
        self.assertEqual(ctx.exception.kind, "runtime_transport")
        self.assertIn("unknown", str(ctx.exception))

    def test_timeout_does_not_retry_and_reaps_the_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "attempts"
            with self.assertRaises(ClientError) as ctx:
                client(timeout=4).apply(_marker=str(path), _delay=30)
            self.assertEqual(ctx.exception.kind, "runtime_timeout")
            attempts = path.read_text().splitlines()
            self.assertEqual(len(attempts), 1)
            with self.assertRaises(ProcessLookupError):
                os.kill(int(attempts[0]), 0)
            self.assertIn("unknown", str(ctx.exception))

    def test_text_only_json_result_is_preserved(self):
        result = CallToolResult(content=[TextContent(type="text", text='{"value":42}')])
        self.assertEqual(unpack(result), {"value": 42})

    def test_unstructured_errors_are_not_success(self):
        result = CallToolResult(isError=True, content=[TextContent(type="text", text="Tool failed")])
        with self.assertRaises(OperationError) as ctx:
            unpack(result)
        self.assertEqual(ctx.exception.error["content"][0]["text"], "Tool failed")

    def test_non_json_or_nonobject_result_is_rejected(self):
        for text in ["null", "[]", "not json", '{"value":NaN}', '{"value":1e999}']:
            with self.subTest(text=text), self.assertRaises(ClientError) as ctx:
                unpack(CallToolResult(content=[TextContent(type="text", text=text)]))
            self.assertEqual(ctx.exception.kind, "invalid_response")

    def test_invalid_parameters_are_rejected_before_launch(self):
        for params in [[], {"number": float("nan")}, {"set": {1, 2}}]:
            with self.subTest(params=params), self.assertRaises(ValueError):
                Client(command=["nonexistent-runtime"]).call("ooxml_view", params)

    def test_stateful_operations_are_not_silently_emulated(self):
        for method in ["ooxml_open", "ooxml_save", "ooxml_close", "ooxml_template_extract_submit"]:
            with self.subTest(method=method), self.assertRaises(ValueError):
                Client(command=["nonexistent-runtime"]).call(method)

    def test_missing_executable_has_a_structured_error(self):
        with self.assertRaises(ClientError) as ctx:
            Client(command=["/this-runtime-does-not-exist"]).man()
        self.assertEqual(ctx.exception.kind, "runtime_unavailable")

    def test_all_convenience_methods_keep_the_canonical_name(self):
        with patch("ooxml_client.client.exchange", new_callable=AsyncMock) as exchange:
            for name in ["man", "inspect", "locate", "view", "apply", "validate", "diff", "render"]:
                getattr(client(), name)(key="value")
                self.assertEqual(exchange.call_args.args[1:3], ("ooxml_" + name, {"key": "value"}))

    def test_invalid_timeouts_and_commands(self):
        for value in [True, 0, -1, float("inf"), float("nan"), "5"]:
            with self.subTest(timeout=value), self.assertRaises(ValueError):
                Client(timeout=value)
        for value in ["shell command", [], [""], [1]]:
            with self.subTest(command=value), self.assertRaises(ValueError):
                Client(command=value)

    def test_request_limit_is_checked_before_launch(self):
        with patch("ooxml_client.transport.MAX_REQUEST_BYTES", 100), self.assertRaises(ClientError) as ctx:
            Client(command=["nonexistent-runtime"]).view(text="a" * 100)
        self.assertEqual(ctx.exception.kind, "request_too_large")

    def test_response_limit_does_not_claim_mutation_failure(self):
        with patch("ooxml_client.transport.MAX_RESPONSE_BYTES", 10), self.assertRaises(ClientError) as ctx:
            client().apply(path="file.docx")
        self.assertEqual(ctx.exception.kind, "response_too_large")
        self.assertIn("unknown", str(ctx.exception))

    def test_async_call_works_inside_an_event_loop(self):
        result = asyncio.run(client().acall("ooxml_view", {"path": "test.docx"}))
        self.assertEqual(result["params"], {"path": "test.docx"})

    def test_sync_call_in_event_loop_explains_async_entry(self):
        async def run():
            with self.assertRaisesRegex(RuntimeError, "acall"):
                client().view(path="test.docx")
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
