"""Select a separately installed runtime without importing its packages."""

import os
from pathlib import Path

from .errors import ClientError

MODULE = "ooxml_operation_engine.mcp_server"


def runtime_command(runtime_python=None):
    value = runtime_python or os.environ.get("OOXML_RUNTIME_PYTHON")
    if not value:
        raise ClientError("runtime_not_configured", "Set OOXML_RUNTIME_PYTHON to the Python executable "
                          "inside your separately installed OOXML runtime, or use --runtime-python.")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ClientError("runtime_not_configured", "The runtime Python executable must have an absolute path.")
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ClientError("runtime_not_available", "The configured runtime Python executable is unavailable.")
    # Preserve the venv entry path: resolving its symlink can select the base interpreter.
    return [str(path), "-I", "-B", "-m", MODULE]
