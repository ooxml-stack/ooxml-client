"""Local stdio sessions using the public MCP SDK."""

import asyncio
import json
import os
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError

from .errors import ClientError, OperationError

MAX_REQUEST_BYTES = 10 * 1024 * 1024
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
UNKNOWN_OUTCOME = "The operation outcome is unknown; inspect outputs before retrying. No retry was attempted."


def _invalid_constant(value):
    raise ValueError(f"Non-finite JSON number: {value}")


def check_params(params):
    if not isinstance(params, dict):
        raise ValueError("params must be a JSON object.")
    try:
        raw = json.dumps(params, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("params must contain JSON-serializable values with finite numbers.") from exc
    if len(raw) > MAX_REQUEST_BYTES:
        raise ClientError("request_too_large", "Parameters exceed the 10 MiB client limit.")


def unpack(result):
    raw = result.model_dump(mode="json", by_alias=True, exclude_none=True)
    try:
        encoded = json.dumps(raw, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ClientError("invalid_response", "Runtime returned non-finite JSON. " + UNKNOWN_OUTCOME) from exc
    if len(encoded) > MAX_RESPONSE_BYTES:
        raise ClientError("response_too_large", "Decoded result exceeds the 16 MiB client limit. " + UNKNOWN_OUTCOME)
    payload = result.structuredContent
    if payload is None and len(result.content) == 1 and result.content[0].type == "text":
        try:
            payload = json.loads(result.content[0].text, parse_constant=_invalid_constant)
        except ValueError:
            pass
    try:
        json.dumps(payload, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise ClientError("invalid_response", "Runtime returned non-finite JSON. " + UNKNOWN_OUTCOME) from exc
    if result.isError:
        raise OperationError(payload if isinstance(payload, dict) else raw)
    if not isinstance(payload, dict):
        raise ClientError("invalid_response", "Runtime did not return an Office JSON object. " + UNKNOWN_OUTCOME)
    return payload


async def _request(command, method, params):
    server = StdioServerParameters(command=command[0], args=command[1:],
                                  env={**os.environ, "PYTHONUTF8": "1", "OOXML_MCP_PROFILE": "core"})
    with tempfile.TemporaryFile(mode="w+") as errors:
        async with stdio_client(server, errlog=errors) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(method, params)


def _leaves(error):
    children = getattr(error, "exceptions", ())
    return [leaf for child in children for leaf in _leaves(child)] if children else [error]


async def exchange(command, method, params, timeout):
    try:
        result = await asyncio.wait_for(_request(command, method, params), timeout)
    except asyncio.TimeoutError as exc:
        raise ClientError("runtime_timeout", "Runtime timed out. " + UNKNOWN_OUTCOME) from exc
    except Exception as exc:
        leaves = _leaves(exc)
        if any(isinstance(leaf, OSError) for leaf in leaves):
            raise ClientError("runtime_unavailable", "Unable to use the configured runtime. " + UNKNOWN_OUTCOME) from exc
        protocol = next((leaf for leaf in leaves if isinstance(leaf, McpError)), None)
        details = protocol.error.model_dump(exclude_none=True) if protocol else None
        raise ClientError("runtime_transport", "MCP session failed. " + UNKNOWN_OUTCOME, details=details) from exc
    return unpack(result)
