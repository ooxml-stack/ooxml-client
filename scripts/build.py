"""Build distributions outside the source checkout."""

import os
import subprocess
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    value = os.environ.get("OOXML_BUILD_OUTPUT")
    if not value:
        raise SystemExit("Set OOXML_BUILD_OUTPUT outside the source checkout.")
    output = Path(value).expanduser().resolve()
    if output.is_relative_to(root):
        raise SystemExit("Build output must be outside the source checkout.")
    return subprocess.call(["uv", "build", "--out-dir", str(output)], cwd=root)


if __name__ == "__main__":
    raise SystemExit(main())
