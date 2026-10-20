"""Self-contained MCP profile probe used by native release acceptance."""

from __future__ import annotations

import asyncio
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .runtime import runtime_command


async def probe(
    profile: str,
    *,
    sample: str | None = None,
    runtime_python: str | None = None,
    runtime_executable: str | None = None,
) -> dict:
    if profile == "pdf":
        return pdf_readability_contract()
    if profile not in {"core", "workflow"}:
        raise ValueError("profile must be core, workflow, or pdf")
    if profile == "workflow" and not sample:
        raise ValueError("workflow probe requires --sample")
    command = runtime_command(runtime_python, runtime_executable)
    env = {
        **os.environ,
        "OOXML_MCP_PROFILE": profile,
        "PYTHONUTF8": "1",
    }
    server = StdioServerParameters(
        command=command[0],
        args=command[1:],
        env=env,
    )
    with open(os.devnull, "w", encoding="utf-8") as errors:
        async with stdio_client(server, errlog=errors) as (read, write):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                listed = await session.list_tools()
                if profile == "core":
                    call = await session.call_tool("ooxml_man", {"topic": "protocol-manifest"})
                else:
                    call = await session.call_tool(
                        "ooxml_text_replace_plan",
                        {"path": sample, "find": "DRAFT", "replace": "DRAFT"},
                    )
    return {
        "profile": profile,
        "server": initialized.serverInfo.model_dump(mode="json"),
        "tool_count": len(listed.tools),
        "tools": [tool.name for tool in listed.tools],
        "call_is_error": bool(call.isError),
        "call_structured": bool(call.structuredContent),
    }


def pdf_readability_contract() -> dict:
    try:
        import fitz  # noqa: F401
    except (ImportError, ModuleNotFoundError):
        return {
            "profile": "pdf",
            "available": False,
            "error": {
                "code": "pdf_readability_unavailable",
                "message": "PDF readability verification is unavailable in this runtime.",
                "recovery": "Use structural Office validation; do not retry an optional dependency import.",
            },
        }
    return {"profile": "pdf", "available": True, "error": None}


def run_probe(profile: str, **kwargs) -> dict:
    return asyncio.run(probe(profile, **kwargs))
