# OOXML Client

Command-line, Python and MCP access to a separately installed local OOXML
Engine. Read document facts, locate objects, apply explicit edits, validate
outputs, compare files and request rendering through the runtime's contracts.
The client uses the public MCP Python SDK and contains no Office execution
implementation or private package dependencies.

## Install the client

```sh
python -m pip install git+https://github.com/ooxml-stack/ooxml-client.git
```

Python 3.10 or newer is required for the client. Use the interpreter version
required by your Engine distribution for the Engine itself.

Install your separately supplied Engine distribution, then set its Python
executable path. Keep that environment separate from the client environment:

```sh
export OOXML_RUNTIME_PYTHON=/absolute/path/to/installed-runtime/bin/python
```

The client does not download an Engine or grant a commercial runtime license.
Without an authorized runtime installation, it cannot edit documents. The
Engine distribution and its dependencies retain their own licenses.

## Discover, read and edit

Parameters and results use the Engine's existing JSON contracts. Discover the
selected runtime before choosing an operation or target:

```sh
ooxml man --params '{"topic":"protocol-manifest"}'
ooxml man --params '{"topic":"operations","format":"docx"}'
ooxml locate --params '{"path":"agreement.docx"}'
ooxml view --params '{"path":"agreement.docx","target":"paragraphs[0]"}'
ooxml apply --params-file edit.json
```

For a runtime supporting `text.set_container`, `edit.json` can contain:

```json
{
  "path": "agreement.docx",
  "operation_id": "text.set_container",
  "target": "paragraphs[0]",
  "params": {"text": "The reviewed agreement."},
  "output_path": "agreement.reviewed.docx"
}
```

Choose `output_path` to preserve the original. Omitting it follows the runtime's
in-place editing behavior. Inspect the result and independently check the saved
file before accepting the edit.

Supported command names are `man`, `inspect`, `locate`, `view`, `apply`,
`validate`, `diff` and `render`. Use `--params` or `--params-file` with the exact
parameters advertised by your runtime. Format/operation support and external
renderer requirements belong to that runtime, not to this client.

## Python

```python
from ooxml_client import Client, OperationError

client = Client(timeout=120)  # reads OOXML_RUNTIME_PYTHON
facts = client.view(path="agreement.docx", target="paragraphs[0]")
try:
    receipt = client.apply(
        path="agreement.docx",
        operation_id="text.set_container",
        target="paragraphs[0]",
        params={"text": "The reviewed agreement."},
        output_path="agreement.reviewed.docx",
    )
except OperationError as error:
    print(error.error)  # unchanged runtime error, including structured details
```

You can pass `runtime_python="/absolute/path/to/runtime/bin/python"` explicitly.
An alternative runtime exposing the same Office tools over MCP stdio can use
`Client(command=["/path/to/runtime", "mcp"])`; arguments are never run through a
shell. Each core call initializes an MCP session and closes its process afterward.
Inside an async application, use `await client.acall("ooxml_view", {"path": "agreement.docx"})`.
Stateful sessions and workflow job lifetimes are not emulated by the Python client.

## Connect an agent through MCP

```json
{
  "mcpServers": {
    "ooxml": {
      "command": "/absolute/path/to/client/bin/ooxml",
      "args": ["--runtime-python", "/absolute/path/to/runtime/bin/python", "mcp"]
    }
  }
}
```

This executes the installed Engine's real MCP server over stdio. The Engine owns
its tool definitions, sessions and jobs. `mcp --profile workflow` selects its
workflow tools. No second set of Office tools is implemented here.

## Errors and privacy

The client makes no network requests and sends no telemetry. Office execution runs in the
configured local process with that process's user permissions. Your agent may
send document text to its model provider; the Engine and configured external
providers can have their own network behavior. This client is not an OS sandbox.

No operation is automatically retried. A timeout, failed process or oversized
response can leave the operation outcome unknown; check the output before
retrying an edit. JSON parameters have a 10 MiB limit and decoded MCP results have
a 16 MiB limit. The response check runs after SDK decoding; it is not a bound on
transport memory usage. The operation timeout defaults to 120 seconds and can be
changed with `--timeout` before the command. SDK process cleanup may add shutdown
time. Runtime stderr is not copied into
client JSON errors.

CLI exit 0 means the MCP tool call completed, not that every reported validation check or
business requirement passed. Read the result's findings and status. Runtime and
transport errors exit 1; invalid client input exits 2. Successful results go to
stdout, client errors to stderr, and MCP inherits the runtime's exit behavior.

## License and verification

The client code is MIT licensed. That license does not cover or relicense the
Engine, its format libraries, third-party dependencies or your documents.
See [runtime boundary](docs/RUNTIME-BOUNDARY.md) for installation and compatibility
requirements and [verified scope](docs/COMPATIBILITY.md) for the real document
cases and their limits. The independently licensed local runtime is the selected delivery
model; a hosted service is not required by the client.

For development, install `.[dev]`, then run `make check` in the authorized test
environment. Build with `OOXML_BUILD_OUTPUT=/path/outside/checkout make build`.
Transport unit tests do not establish Office behavior. Real-runtime evidence
must identify the installed Engine, client source and the cases actually run.
