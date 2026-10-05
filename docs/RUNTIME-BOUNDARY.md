# Local runtime boundary

The public package contains only client transport, CLI handling and error
presentation. Its built wheel and source archive must not contain Engine code,
private Git URLs, customer documents, model transcripts or runtime archives.

The supported Python runtime entrypoint is
`ooxml_operation_engine.mcp_server` for both core operations and persistent agent
connections. It runs inside the separately installed runtime environment using
Python isolated mode.
The client never imports those modules into its own interpreter.

## Wire contract

Core calls use the public MCP Python SDK: initialize a stdio session, call one
tool, and shut down. The SDK handles JSON-RPC framing, correlation and process
cleanup. Office structured results and tool errors are preserved; protocol
errors remain attached to transport failures. JSON text results from older MCP
servers are also supported. Engine diagnostics belong on stderr.

The runtime inherits the caller's environment and working directory. Core calls
select the core profile; the persistent MCP entry supports core and workflow
profiles. A separate process keeps Python dependencies separate, but is not a
security sandbox. Use a runtime you trust.

Parameters, object addresses and operation schemas come from runtime discovery.
The client does not synthesize capability claims, repair results, retry failed
mutations or translate unavailable validation into success. It does not retain
stateful sessions between calls. Use the Engine MCP process for agent sessions
and workflow jobs.

## Installation contract

A runtime distribution must install independently, declare its supported
platform/interpreter, include its applicable licenses and third-party notices,
and identify its source versions and artifacts. The user must not need private
Git credentials or a development workspace after receiving the distribution.
The current client accepts the runtime interpreter explicitly; it does not
silently choose another Python or download executable code.

Client and runtime licenses are independent. An open-source client can be
modified under its license. Its source availability is not a grant to copy or
redistribute proprietary runtime components. Existing upstream permissions
remain intact. A runtime delivered as Python files is inspectable; commercial
terms do not make its implementation technically inaccessible.

## Release checks

Verify the built client in a fresh environment without any Engine distribution
installed there. Run it against a separately installed runtime and record that
runtime's source/package identities. Include a real read/edit/validate workflow
for each advertised format, with original-file preservation and independent
output readback. Test an invalid request and verify that it does not silently
succeed. Initialize the real MCP process and inspect its tool list.

Check the client wheel and source archive for private dependencies or source.
Keep generated evidence and packages outside the checkout. Real document
acceptance and transport-only unit tests must have separate scope labels.
