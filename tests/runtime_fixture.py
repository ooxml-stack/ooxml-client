"""A real MCP subprocess for client transport tests; no Office implementation."""

import asyncio
import json
import os
from pathlib import Path

from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

from ooxml_client.client import COMMANDS

server = Server("client-transport-fixture")


@server.list_tools()
async def tools():
    return [Tool(name="ooxml_" + name, inputSchema={"type": "object"}) for name in COMMANDS]


@server.call_tool()
async def call(name, arguments):
    if marker := arguments.get("_marker"):
        with Path(marker).open("a") as output:
            output.write(str(os.getpid()) + "\n")
    if arguments.get("_exit"):
        os._exit(7)
    if delay := arguments.get("_delay"):
        await asyncio.sleep(delay)
    payload = arguments.get("_error", {"method": name, "params": arguments})
    return CallToolResult(isError="_error" in arguments, structuredContent=payload,
                          content=[TextContent(type="text", text=json.dumps(payload))])


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


asyncio.run(main())
