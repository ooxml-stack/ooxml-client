"""Public client; Office execution belongs to the separately installed runtime."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _package_version

from .client import Client
from .errors import ClientError, OperationError

__all__ = ["Client", "ClientError", "OperationError"]

_FALLBACK_VERSION = "0.1.58"

try:
    __version__ = _package_version("ooxml-client")
except PackageNotFoundError:
    __version__ = _FALLBACK_VERSION
