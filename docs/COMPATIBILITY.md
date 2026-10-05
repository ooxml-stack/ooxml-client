# Verified client scope

Client 0.1.0 was exercised against an independently installed Engine 0.1.37,
source revision `46a79abcc59f80e25da58d79a62af57db59c8e78`, on macOS arm64.
The client and runtime used separate environments. Installing the client did
not install Engine, Core or the Office format packages.

The client uses the MCP 1.x Python SDK. Each core call initializes a session,
forwards a tool request and preserves its structured response. Capability
names and parameters come from the selected runtime; an Engine version number
alone is not a promise that every operation exists.

## Real document cases

Synthetic, locally generated documents were used for these checks:

| Format | Explicit edit | Independently checked after save |
| --- | --- | --- |
| DOCX | Replace one paragraph's text | Replacement text and the untouched second paragraph |
| PPTX | Replace one shape's text | Replacement text and the untouched second shape |
| XLSX | Set A1 to numeric 42 | Numeric cell value and the untouched B1 formula |

Each case passed inspect, locate, view, apply, structural validate and diff.
The original file's SHA-256 remained unchanged. Output contents were checked
independently through ZIP/XML readback. An invalid operation returned a
structured error without modifying the original or creating its requested output.

The persistent MCP launcher initialized the real runtime and listed its core
8-tool and workflow 10-tool profiles. Listing workflow tools does not prove a
complete template job lifecycle.

## Limits

These are interface and explicit edit checks, not a general Office fidelity
benchmark. Rendering, native Office opening, formula recalculation, arbitrary
document preservation, template workflows and model task completion were not
measured in this client acceptance. The `render` command forwards the runtime
contract; its providers must be installed and verified separately.

A separately supplied, authorized runtime is required. This client release does
not announce a public Engine download or complete the runtime's commercial
license and distribution review. Existing component licenses remain in force.
