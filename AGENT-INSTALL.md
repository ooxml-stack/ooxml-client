# Install with your agent (public contract, no secrets)

This document is the complete install contract for a customer agent on a clean
Apple Silicon Mac. It references online URLs only. It contains no tokens, no
private URLs and no source paths. The agent receives one private install URL
from us (delivered out of band) plus this document.

## 0. Compatibility gate

Check before downloading anything; refuse cleanly on mismatch:

- Darwin + arm64 (`uname -s` = Darwin, `uname -m` = arm64)
- macOS 26 or compatible
- Python 3.12 available (`python3 --version`)
- No `sudo`, no `curl | sh`, no source checkouts

Incompatibility error: `incompatible_platform`.

## 1. Fetch the release manifest

`GET <private-install-url>` returns the staging release manifest (schema 1):
`artifact_id`, `client_commit`, `skill_commit`, `files[]` with per-file
`filename`, `size`, `sha256`, `component` and `url`.

Error: `download_failed` when the manifest or any file is unreachable.

## 2. Download and verify before executing anything

For each required file: download to an isolated directory, then verify the
registered size and SHA-256 before unpacking or installing. Refuse on any
mismatch (`checksum_failed`), wrong artifact (`install_failed`) or wrong
platform (`incompatible_platform`). Never install unverified bytes.

## 3. Install into an isolated user directory

- Create an independent venv; install with `--no-deps` for the product wheels
  (client, manufactured runtime).
- Third-party dependencies come from the frozen wheelhouse with `--no-index`.
- Run `pip check`.
- Error taxonomy: `install_failed`, `checksum_failed`, `activation_failed`,
  `mcp_configuration_failed`, `skill_install_failed`, `smoke_test_failed`.

## 4. Activate the staging license

`ooxml activate --license <verified staging license file>` then
`ooxml status` — the answer must be `installed: true` with the release
`artifact_id` and `serving: active`. A forged, edited, expired or
wrong-artifact license is refused (`activation_failed`).

## 5. Install the customer-facing skill and register local MCP

- Install the `ooxml` customer skill into the agent's user-level skill
  directory; back up a same-named older skill; never silently overwrite an
  incompatible version.
- Register the local MCP: `ooxml register claude --scope local` or
  `ooxml register codex` (back up the previous configuration first).
- Restart or reconnect MCP, then smoke-test: initialize, `tools/list`, one real
  document-free call. The collections must match `contracts/mcp-contract.json`
  shipped by the client release (core 8, workflow 10).

Errors: `mcp_configuration_failed`, `skill_install_failed`, `smoke_test_failed`.

## 6. Acceptance smoke (local, offline afterwards)

- CLI: Word apply to a NEW file + validate; Excel cell apply + validate; a
  broken pptx is refused with its real validation reason.
- Offline: after activation the CLI and the local MCP work with Wi-Fi off.
- Output exists only on the customer Mac; nothing is uploaded.

Result: structured `success` plus the per-step results above.

## 7. Idempotency and recovery

Re-running is safe: verified downloads, isolated directories and structured
launchers make each step idempotent. Uninstall: remove the isolated venv,
`~/.ooxml`, the registered MCP entry and the installed skill; restore the
backed-up configuration.
