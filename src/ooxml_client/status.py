"""Report local activation and real runtime serving status."""

import json
from pathlib import Path

from .client import Client
from .distribute import LICENSE_DIR
from .errors import ClientError


def status(
    runtime_python=None,
    runtime_executable=None,
    *,
    license_dir=None,
    timeout=120,
):
    """Return a redacted activation and serving status object."""
    directory = Path(license_dir) if license_dir is not None else LICENSE_DIR
    license_path = directory / "license.json"
    if not license_path.is_file():
        return {
            "installed": False,
            "serving": "inactive",
            "reason": "license_missing",
        }
    try:
        payload = json.loads(license_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {
            "installed": False,
            "serving": "inactive",
            "reason": "license_unreadable",
        }
    base = {
        "installed": True,
        "license_id": payload.get("license_id"),
        "artifact_id": payload.get("artifact_id"),
        "expiry": payload.get("expiry"),
    }
    try:
        manifest = Client(
            runtime_python,
            runtime_executable=runtime_executable,
            timeout=timeout,
        ).man(topic="protocol-manifest")
    except ClientError as exc:
        return {**base, "serving": "inactive", "error": exc.as_dict()}
    return {
        **base,
        "serving": "active",
        "runtime_version": manifest.get("runtime_version"),
        "build": manifest.get("build"),
    }
