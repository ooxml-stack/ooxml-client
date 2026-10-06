# Contributing to ooxml-client

`ooxml-client` is the thin client used to reach a running operation engine.

## Setup

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
```

## Change workflow

1. Branch from `main`.
2. `make check` runs the full local gate (tests, lint, types, coverage).
3. Add behaviour tests under `tests/` and keep the public methods annotated and
   documented; `make typecheck` is a ratchet on `quality-baselines.json`.
4. Update `CHANGELOG.md` under `Unreleased`; `0.1.0` is the first documented
   release.
5. Examples live in `examples/client.py` and are executed by the test suite.

## Gate contracts

| Gate | Command | Contract |
| --- | --- | --- |
| Lint | `python3 scripts/quality_gate.py ruff` | Zero findings for `[tool.ruff.lint]` |
| Format | `python3 scripts/format_gate.py` | `ruff format --check` on changed files only |
| Types | `python3 scripts/quality_gate.py pyright` | pyright errors must not exceed the baseline |
| Coverage | `make coverage` | `.coveragerc` floor, currently 95% |

## Reporting problems

Include the command, the engine version you targeted, the observed response and
the tested commit.
