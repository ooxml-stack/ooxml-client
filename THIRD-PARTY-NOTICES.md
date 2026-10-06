# Third-party notices

Runtime dependencies of this package and the license each is distributed under.
`scripts/check_dependency_notices.py` fails the lint gate when a declared
runtime dependency is missing from this table, so the inventory cannot drift.

Licenses are read from each project's published package metadata (PyPI JSON
API). The private `ooxml-*` packages are first-party components of this
workspace: they are pinned by tag in `pyproject.toml` and carry the same MIT
license as this repository (see `LICENSE`), so they are not repeated here.

| Package | License | Upstream |
| --- | --- | --- |
| `mcp` | MIT | https://pypi.org/project/mcp/ |
