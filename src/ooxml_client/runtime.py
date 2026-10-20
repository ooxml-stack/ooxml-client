"""Select a separately installed runtime without importing its packages."""

import os
import sys
from pathlib import Path

from .errors import ClientError

MODULE = "ooxml_operation_engine.mcp_server"
NATIVE_COMMAND = ("serve", "--transport", "stdio")


def _executable(value, kind):
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ClientError("runtime_not_configured", f"The {kind} must have an absolute path.")
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ClientError("runtime_not_available", f"The configured {kind} is unavailable.")
    return path


def _native_runtime(runtime_executable=None):
    """Return an explicitly configured native engine executable."""
    value = runtime_executable or os.environ.get("OOXML_RUNTIME_EXECUTABLE")
    return _executable(value, "runtime executable") if value else None


def runtime_command(runtime_python=None, runtime_executable=None):
    """Return the command that starts the configured runtime's MCP server.

    Native runtime selection wins over the legacy Python path. The legacy
    runtime_python path remains unchanged for wheel-based installations.
    """
    native = _native_runtime(runtime_executable)
    if native is not None:
        return [str(native), *NATIVE_COMMAND]
    value = runtime_python or os.environ.get("OOXML_RUNTIME_PYTHON")
    if value:
        path = _executable(value, "runtime Python executable")
        # Preserve the venv entry path: resolving its symlink can select the base interpreter.
        return [str(path), "-I", "-B", "-m", MODULE]
    sibling = Path(sys.executable).resolve().with_name("ooxml-engine")
    if sibling.is_file() and os.access(sibling, os.X_OK):
        return [str(sibling), *NATIVE_COMMAND]
    raise ClientError(
        "runtime_not_configured",
        "Set OOXML_RUNTIME_EXECUTABLE to the native OOXML engine executable, "
        "or set OOXML_RUNTIME_PYTHON for the legacy Python runtime.",
    )
