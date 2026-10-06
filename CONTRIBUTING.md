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

## Versioning and release tagging

- **Source of truth.** `src/ooxml_client/__init__.py` (currently `0.1.0`). Version bumps land in the same commit as the
  behaviour change they describe; nothing else in the tree re-states the number.
- **Scheme.** SemVer (`MAJOR.MINOR.PATCH`); a pre-1.0 minor may carry breaking changes, which the changelog calls out.
- **Dependency order.** A stack release moves bottom-up: `ooxml-spec` →
  `ooxml-stubs` / `ooxml-test-framework` → `ooxml-core` → the document libraries
  (`python-docx`, `python-pptx`, `python-xlsx`) → `ooxml-operation-engine` →
  `ooxml-apps`. A dependent repository pins the tag of the repository below it
  and never a branch head.
- **Pins.** Dependencies on sibling repositories are pinned by tag in
  `pyproject.toml` (and recorded in `uv.lock`); moving a pin is a deliberate
  change with its own pull request and changelog line, never a side effect of an
  unrelated change.
- **Tags.** A release tag names the released artefact and is created from the
  release commit; the release workflow fails when the tag and the packaged
  version disagree (see `.github/workflows/release.yml`). Tags are never moved
  after publication — a correction is a new tag.
- **Changelog.** Every user-visible change gets an entry: `CHANGELOG.md` under
  Keep a Changelog, with breaking changes called out explicitly.
